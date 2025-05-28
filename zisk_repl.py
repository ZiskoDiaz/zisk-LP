#!/usr/bin/env python3
import re
import sys
from typing import Any, Dict, List, Tuple, Optional, Union

# --- EXCEPCIONES ---
class ZiskError(Exception):
    def __init__(self, mensaje: str, linea: int = 0, columna: int = 0):
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna
        super().__init__(f"Error en línea {linea}, columna {columna}: {mensaje}")

class ZiskTypeError(ZiskError):
    pass

class BreakException(Exception): # Usada para implementar 'break' en bucles
    pass

class ContinueException(Exception): # Usada para implementar 'continua' en bucles
    pass

class ReturnException(Exception): # Usada para implementar 'retorna' desde funciones/métodos
    def __init__(self, value: Any = None):
        self.value = value
        super().__init__("Excepción de retorno (esto no debería ser visible al usuario)")

# --- LEXER ---
class ZiskLexer:
    def __init__(self):
        self.tokens_spec = [
            # Palabras clave (ordenadas por longitud descendente para evitar ambigüedades con prefijos)
            ('HACER_MIENTRAS',  r'hacer_mientras'),
            ('VERDADERO',       r'verdadero'),
            ('CONTINUA',        r'continua'),
            ('EXTIENDE',        r'extiende'),
            ('ENTONCES',        r'entonces'),
            ('ESTATICO',        r'estatico'),
            ('FUNCION',         r'funcion'),
            ('IMPORTA',         r'importa'),
            ('INGRESAR',        r'ingresar'),
            ('MIENTRAS',        r'mientras'),
            ('MOSTRAR',         r'mostrar'),
            ('PRIVADO',         r'privado'),
            ('PUBLICO',         r'publico'),
            ('RETORNA',         r'retorna'),
            ('FINALLY',         r'finally'),
            ('AWAIT',           r'await'),
            ('CLASE',           r'clase'),
            ('CONST',           r'const'),
            ('DESDE',           r'desde'),
            ('FALSO',           r'falso'),
            ('NUEVO',           r'nuevo'),
            ('SINO',            r'sino'),
            ('ASYNC',           r'async'),
            ('BREAK',           r'break'),
            ('CATCH',           r'catch'),
            ('COMO',            r'como'),
            ('ESTE',            r'este'),
            ('PARA',            r'para'),
            ('NULO',            r'nulo'),
            ('TIPO',            r'(entero|decimal|texto|booleano|lista|objeto|funcion|clase)'), # Debe ir antes de IDENTIFICADOR
            ('VAR',             r'var'),
            ('SI',              r'si'),
            ('EN',              r'en'),
            ('TRY',             r'try'),
            # Identificadores
            ('IDENTIFICADOR',   r'[a-zA-Z_][a-zA-Z0-9_]*'), # Tipos (entero, etc.) deben ir antes
            # Literales
            ('NUMERO',          r'\d+(\.\d+)?'),
            ('CADENA',          r'"(?:[^"\\]|\\.)*"'),
            # Operadores (los de múltiples caracteres primero)
            ('OPERADOR',        r'==|!=|<=|>=|\|\||&&|\+=|-=|\*=|/=|%=|[\+\-\*/%=<>!]'),
            # Delimitadores
            ('PARENTESIS',      r'[\(\)]'),
            ('LLAVE',           r'[\{\}]'),
            ('CORCHETE',        r'[\[\]]'),
            ('COMA',            r','),
            ('PUNTO',           r'\.'),
            ('PUNTO_COMA',      r';'),
            ('DOS_PUNTOS',      r':'),
            # Comentarios y Espacios en Blanco (se ignorarán o manejarán especialmente)
            ('COMENTARIO_LINEA',r'(//|#)[^\n]*'),
            ('COMENTARIO_BLOQUE',r'(/\*[\s\S]*?\*/|###[\s\S]*?###)'),
            ('ESPACIO',         r'\s+'),
            ('NO_VALIDO',       r'.'), # Para capturar caracteres no válidos al final
        ]
        # Compilar las expresiones regulares una vez
        self.regex_compilado = re.compile('|'.join(f'(?P<{par[0]}>{par[1]})' for par in self.tokens_spec))
        self.linea_actual = 1
        self.columna_actual = 1


    def tokenize(self, code: str) -> List[Tuple[str, str, int, int]]:
        tokens_encontrados = []
        posicion = 0
        
        # Normalizar saltos de línea para un manejo consistente
        code_lines = code.splitlines(keepends=True)
        
        linea_num = 1
        col_inicio_linea = 0

        while posicion < len(code):
            match = self.regex_compilado.match(code, posicion)
            if not match:
                # Esto no debería ocurrir si NO_VALIDO está al final de tokens_spec
                # Pero si ocurre, es un error en el lexer o un caracter inesperado no cubierto
                # Avanzamos un caracter para evitar bucle infinito
                col = posicion - col_inicio_linea + 1
                raise ZiskError(f"Carácter inesperado no reconocido por el lexer: '{code[posicion]}'", linea_num, col)

            tipo_token = match.lastgroup
            valor_token = match.group(tipo_token)
            col_actual = match.start() - col_inicio_linea + 1

            if tipo_token not in ['COMENTARIO_LINEA', 'COMENTARIO_BLOQUE', 'ESPACIO']:
                if tipo_token == 'NO_VALIDO':
                    raise ZiskError(f"Carácter no válido: '{valor_token}'", linea_num, col_actual)
                tokens_encontrados.append((tipo_token, valor_token, linea_num, col_actual))
            
            # Actualizar posición, línea y columna
            posicion = match.end()
            
            # Contar saltos de línea en el token actual (importante para comentarios de bloque)
            saltos_linea_en_token = valor_token.count('\n')
            if saltos_linea_en_token > 0:
                linea_num += saltos_linea_en_token
                col_inicio_linea = match.start() + valor_token.rfind('\n') + 1
        
        return tokens_encontrados


# --- PARSER ---
class ZiskParser:
    def __init__(self):
        self.tokens: List[Tuple[str, str, int, int]] = []
        self.token_index: int = 0
        self.current_token: Optional[Tuple[str, str, int, int]] = None
        self.scopes: List[Dict[str, Any]] = [{}] # Pila de ámbitos
        self.current_class: Optional[str] = None # Nombre de la clase actual siendo parseada

    def _actualizar_token_actual(self):
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        else:
            self.current_token = None # Fin de los tokens

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def current_scope(self) -> Dict[str, Any]:
        return self.scopes[-1]

    def variable_declared_in_current_scope(self, name: str) -> bool:
        return name in self.current_scope()

    def variable_declared(self, name: str) -> bool:
        for scope in reversed(self.scopes):
            if name in scope:
                return True
        return False

    def parse(self, tokens: List[Tuple[str, str, int, int]]):
        self.tokens = tokens
        self.token_index = 0
        self._actualizar_token_actual()
        return self.parse_programa()

    def parse_programa(self):
        declaraciones = []
        while self.current_token:
            declaraciones.append(self.parse_declaracion())
        return ('PROGRAMA', declaraciones)

    def parse_declaracion(self):
        if not self.current_token:
            # Esto podría ocurrir si se espera una declaración pero no hay más tokens
            # Usar la info del último token si existe, o línea/col 1
            line, col = (self.tokens[-1][2], self.tokens[-1][3]) if self.tokens else (1,1)
            raise ZiskError("Se esperaba una declaración, pero se encontró el fin del archivo.", line, col)

        token_type = self.current_token[0]
        
        if token_type == 'FUNCION':
            return self.parse_funcion()
        elif token_type == 'CLASE':
            return self.parse_clase()
        elif token_type == 'VAR':
            return self.parse_declaracion_variable()
        elif token_type == 'CONST':
            return self.parse_declaracion_constante()
        elif token_type == 'IMPORTA':
            return self.parse_importa()
        # ASYNC, TRY, BREAK, CONTINUA se manejan como sentencias
        # elif token_type in ['ASYNC', 'TRY', 'BREAK', 'CONTINUA']:
        #     return self.parse_sentencia_especial() # Necesitaría esta función
        else:
            return self.parse_sentencia()

    def parse_funcion(self):
        self.consume('FUNCION')
        nombre_token = self.consume('IDENTIFICADOR')
        nombre = nombre_token[1]
        
        if not re.match(r'^[a-z_][a-zA-Z0-9_]*$', nombre): # Permitir _ al inicio para privados "por convención"
            raise ZiskError("Nombre de función debe usar camelCase o snake_case comenzando con minúscula.", nombre_token[2], nombre_token[3])

        self.consume('PARENTESIS', '(')
        parametros = []
        self.enter_scope() # Entrar al ámbito para parámetros
        while self.current_token and self.current_token[1] != ')':
            if len(parametros) > 0:
                self.consume('COMA')
            
            param_token = self.consume('IDENTIFICADOR')
            param_nombre = param_token[1]
            tipo_param = None
            if self.current_token and self.current_token[0] == 'DOS_PUNTOS':
                self.consume('DOS_PUNTOS')
                tipo_param_token = self.consume('TIPO')
                tipo_param = tipo_param_token[1]
            parametros.append((param_nombre, tipo_param))
            self.current_scope()[param_nombre] = ('PARAM', tipo_param) # Registrar parámetro en el ámbito
        
        self.consume('PARENTESIS', ')')
        
        tipo_retorno = None
        if self.current_token and self.current_token[0] == 'DOS_PUNTOS':
            self.consume('DOS_PUNTOS')
            tipo_retorno_token = self.consume('TIPO')
            tipo_retorno = tipo_retorno_token[1]
        
        # El cuerpo de la función se parsea en su propio ámbito
        cuerpo = self.parse_bloque(is_function_body=True) # No se sale del ámbito aquí, parse_bloque lo hace si is_function_body
        # self.exit_scope() # Es manejado por parse_bloque o después de parse_bloque
        
        return ('FUNCION', nombre, parametros, tipo_retorno, cuerpo)

    def parse_clase(self):
        self.consume('CLASE')
        nombre_token = self.consume('IDENTIFICADOR')
        nombre = nombre_token[1]
        
        if not re.match(r'^[A-Z][a-zA-Z0-9_]*$', nombre):
            raise ZiskError("Nombre de clase debe usar PascalCase.", nombre_token[2], nombre_token[3])

        superclase = None
        if self.current_token and self.current_token[0] == 'EXTIENDE':
            self.consume('EXTIENDE')
            superclase_token = self.consume('IDENTIFICADOR')
            superclase = superclase_token[1]
        
        old_class = self.current_class
        self.current_class = nombre
        
        self.enter_scope() # Ámbito para la clase
        self.consume('LLAVE', '{')
        
        miembros = []
        while self.current_token and self.current_token[1] != '}':
            # Modificadores de acceso y estático
            es_estatico = False
            es_publico = True # Por defecto
            
            while self.current_token and self.current_token[0] in ['ESTATICO', 'PUBLICO', 'PRIVADO']:
                mod_token = self.consume() # Consume el modificador
                if mod_token[0] == 'ESTATICO':
                    es_estatico = True
                elif mod_token[0] == 'PUBLICO':
                    es_publico = True
                elif mod_token[0] == 'PRIVADO':
                    es_publico = False
            
            if self.current_token and self.current_token[0] in ['VAR', 'CONST']:
                miembros.append(self.parse_declaracion_miembro_clase(es_estatico, es_publico))
            elif self.current_token and self.current_token[0] == 'FUNCION':
                miembros.append(self.parse_metodo_clase(es_estatico, es_publico))
            else:
                if not self.current_token:
                     raise ZiskError("Se esperaba un miembro de clase o '}' pero se encontró el fin del archivo.", self.tokens[-1][2], self.tokens[-1][3])
                raise ZiskError(f"En una clase solo se permiten variables, constantes y métodos. Encontrado: {self.current_token[0]}", self.current_token[2], self.current_token[3])
        
        self.consume('LLAVE', '}')
        self.exit_scope() # Salir del ámbito de la clase
        self.current_class = old_class
        
        return ('CLASE', nombre, superclase, miembros)

    def parse_declaracion_miembro_clase(self, es_estatico: bool, es_publico: bool):
        # Los modificadores ya fueron consumidos antes de llamar a esta función
        token_type = self.current_token[0]
        if token_type == 'VAR':
            # Pasar los modificadores a la declaración de variable
            return self.parse_declaracion_variable(es_miembro=True, es_estatico_miembro=es_estatico, es_publico_miembro=es_publico)
        elif token_type == 'CONST':
            # Las constantes de clase suelen ser implícitamente estáticas, pero aquí respetamos el modificador 'estatico'
            return self.parse_declaracion_constante(es_miembro=True, es_estatico_miembro=es_estatico, es_publico_miembro=es_publico)
        else: # Esto no debería ocurrir si la lógica en parse_clase es correcta
            raise ZiskError("Se esperaba declaración de variable o constante de miembro.", self.current_token[2], self.current_token[3])


    def parse_metodo_clase(self, es_estatico_ya_parseado: bool, es_publico_ya_parseado: bool):
        # Los modificadores (estatico, publico, privado) ya fueron consumidos
        self.consume('FUNCION')
        nombre_token = self.consume('IDENTIFICADOR')
        nombre = nombre_token[1]
        
        # Convenciones de nombrado para métodos
        if es_publico_ya_parseado and not re.match(r'^[a-z_][a-zA-Z0-9_]*$', nombre):
            raise ZiskError("Nombre de método público debe usar camelCase o snake_case comenzando con minúscula.", nombre_token[2], nombre_token[3])
        elif not es_publico_ya_parseado and not (nombre.startswith('_') or re.match(r'^[a-z_][a-zA-Z0-9_]*$', nombre)): # Permitir _ o camelCase/snake_case
             if not nombre.startswith('_'):
                raise ZiskError("Nombre de método privado convencionalmente debe comenzar con '_'.", nombre_token[2], nombre_token[3])


        self.consume('PARENTESIS', '(')
        parametros = []
        self.enter_scope() # Ámbito para parámetros del método
        
        # 'este' es implícito para métodos de instancia, no se declara como parámetro
        # if not es_estatico_ya_parseado:
        #     self.current_scope()['este'] = ('OBJETO_ACTUAL', self.current_class)

        while self.current_token and self.current_token[1] != ')':
            if len(parametros) > 0:
                self.consume('COMA')
            
            param_token = self.consume('IDENTIFICADOR')
            param_nombre = param_token[1]
            if param_nombre == 'este':
                raise ZiskError("'este' es una palabra reservada y no puede ser un nombre de parámetro.", param_token[2], param_token[3])

            tipo_param = None
            if self.current_token and self.current_token[0] == 'DOS_PUNTOS':
                self.consume('DOS_PUNTOS')
                tipo_param_token = self.consume('TIPO')
                tipo_param = tipo_param_token[1]
            parametros.append((param_nombre, tipo_param))
            self.current_scope()[param_nombre] = ('PARAM', tipo_param)
        
        self.consume('PARENTESIS', ')')
        
        tipo_retorno = None
        if self.current_token and self.current_token[0] == 'DOS_PUNTOS':
            self.consume('DOS_PUNTOS')
            tipo_retorno_token = self.consume('TIPO')
            tipo_retorno = tipo_retorno_token[1]
        
        cuerpo = self.parse_bloque(is_function_body=True) # Ámbito manejado por parse_bloque
        
        return ('METODO', nombre, parametros, tipo_retorno, cuerpo, es_estatico_ya_parseado, es_publico_ya_parseado)

    def parse_declaracion_variable(self, es_miembro=False, es_estatico_miembro=False, es_publico_miembro=True):
        start_token = self.consume('VAR')
        nombre_token = self.consume('IDENTIFICADOR')
        nombre = nombre_token[1]
        
        if not re.match(r'^[a-z_][a-zA-Z0-9_]*$', nombre): # Permitir _ al inicio para privados "por convención"
            raise ZiskError("Nombre de variable debe usar camelCase o snake_case comenzando con minúscula.", nombre_token[2], nombre_token[3])
        
        # Para variables locales (no miembros) o miembros de clase (si se desea chequear redeclaración en el mismo nivel de clase)
        # Aquí, si es_miembro, la "declaración" se refiere a la definición dentro de la clase.
        # El chequeo de `variable_declared_in_current_scope` es más apropiado para variables locales.
        if not es_miembro and self.variable_declared_in_current_scope(nombre):
            raise ZiskError(f"Variable '{nombre}' ya declarada en este ámbito.", nombre_token[2], nombre_token[3])

        tipo = None
        valor = None # Nodo AST del valor
        
        if self.current_token and self.current_token[0] == 'DOS_PUNTOS':
            self.consume('DOS_PUNTOS')
            tipo_token = self.consume('TIPO')
            tipo = tipo_token[1]
        
        if self.current_token and self.current_token[0] == 'OPERADOR' and self.current_token[1] == '=':
            self.consume('OPERADOR', '=')
            valor = self.parse_expresion()
        
        if not es_miembro:
            self.current_scope()[nombre] = ('VAR', tipo)
        
        self.consume_optional_semicolon()
        
        if es_miembro:
            return ('DECLARACION_VAR_MIEMBRO', nombre, tipo, valor, es_estatico_miembro, es_publico_miembro)
        return ('DECLARACION_VAR', nombre, tipo, valor)


    def parse_declaracion_constante(self, es_miembro=False, es_estatico_miembro=False, es_publico_miembro=True):
        self.consume('CONST')
        nombre_token = self.consume('IDENTIFICADOR')
        nombre = nombre_token[1]
        
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', nombre):
            raise ZiskError("Nombre de constante debe usar MAYUSCULAS_CON_GUIONES_BAJOS.", nombre_token[2], nombre_token[3])
        
        if not es_miembro and self.variable_declared_in_current_scope(nombre):
            raise ZiskError(f"Constante '{nombre}' ya declarada en este ámbito.", nombre_token[2], nombre_token[3])

        tipo = None
        if self.current_token and self.current_token[0] == 'DOS_PUNTOS':
            self.consume('DOS_PUNTOS')
            tipo_token = self.consume('TIPO')
            tipo = tipo_token[1]
        
        self.consume('OPERADOR', '=') # Constantes deben ser inicializadas
        valor = self.parse_expresion()
        
        if not es_miembro:
            self.current_scope()[nombre] = ('CONST', tipo)
        
        self.consume_optional_semicolon()

        if es_miembro:
            return ('DECLARACION_CONST_MIEMBRO', nombre, tipo, valor, es_estatico_miembro, es_publico_miembro)
        return ('DECLARACION_CONST', nombre, tipo, valor)


    def parse_sentencia(self):
        if not self.current_token:
            line, col = (self.tokens[-1][2], self.tokens[-1][3]) if self.tokens else (1,1)
            raise ZiskError("Se esperaba una sentencia, pero se encontró el fin del archivo.", line, col)

        token_type = self.current_token[0]

        if token_type == 'SI':
            return self.parse_si()
        elif token_type == 'MIENTRAS':
            return self.parse_mientras()
        elif token_type == 'PARA':
            return self.parse_para()
        elif token_type == 'HACER_MIENTRAS':
            return self.parse_hacer_mientras()
        elif token_type == 'MOSTRAR':
            return self.parse_mostrar()
        elif token_type == 'INGRESAR': # Ingresar es una expresión, pero puede ser una sentencia si se usa su resultado o no
            # Si `ingresar` se usa como sentencia, es una expresión-sentencia
            expr = self.parse_expresion() 
            self.consume_optional_semicolon()
            return expr
        elif token_type == 'RETORNA':
            return self.parse_retorna()
        elif token_type == 'BREAK':
            return self.parse_break()
        elif token_type == 'CONTINUA':
            return self.parse_continua()
        elif token_type == 'TRY':
            return self.parse_try_catch()
        elif token_type == 'LLAVE' and self.current_token[1] == '{': # Bloque explícito
            return self.parse_bloque()
        else: # Expresión-sentencia (ej. asignación, llamada a función)
            expr = self.parse_expresion()
            self.consume_optional_semicolon()
            return expr

    # --- JERARQUÍA DE EXPRESIONES (Precedencia de operadores) ---
    # parse_expresion (alias para el nivel más bajo de precedencia que no es asignación directa)
    # parse_expresion_asignacion (=, +=, -=, etc.)
    # parse_expresion_logica_o (||)
    # parse_expresion_logica_y (&&)
    # parse_expresion_comparacion (==, !=, <, >, <=, >=)
    # parse_expresion_adicion (+, -)
    # parse_expresion_multiplicacion (*, /, %)
    # parse_expresion_unaria (-, !)
    # parse_expresion_llamada_o_acceso ( (), [], . ) --- ¡NUEVO NIVEL!
    # parse_expresion_primaria (literales, identificadores, expresiones entre paréntesis, nuevo)

    def parse_expresion(self):
        return self.parse_expresion_asignacion()

    def parse_expresion_asignacion(self):
        # La asignación es asociativa a la derecha: a = b = c  es a = (b = c)
        # Pero la parseamos de izquierda a derecha y luego verificamos.
        # Para manejar correctamente la asociatividad a la derecha, el lado derecho de la asignación
        # debe ser parseado con la misma o menor precedencia.
        
        izquierda = self.parse_expresion_logica_o() # Parsear el operando izquierdo
        
        if self.current_token and self.current_token[0] == 'OPERADOR' and \
           self.current_token[1] in ['=', '+=', '-=', '*=', '/=', '%=']:
            
            op_token = self.consume('OPERADOR') # Consume el operador de asignación
            operador = op_token[1]

            # Validación del lado izquierdo (L-value)
            # Debe ser un identificador, un acceso a miembro (obj.prop) o un acceso a índice (lista[idx])
            if not (isinstance(izquierda, tuple) and 
                    izquierda[0] in ['IDENTIFICADOR', 'ACCESO_MIEMBRO', 'ACCESO_INDICE']):
                raise ZiskError("El lado izquierdo de una asignación debe ser una variable, propiedad o elemento de lista.", 
                               op_token[2], op_token[3]) # Usar línea/col del operador
            
            derecha = self.parse_expresion_asignacion() # Recursión para asociatividad a la derecha
            
            return ('ASIGNACION', operador, izquierda, derecha)
        
        return izquierda


    def parse_expresion_logica_o(self):
        izquierda = self.parse_expresion_logica_y()
        while self.current_token and self.current_token[0] == 'OPERADOR' and self.current_token[1] == '||':
            operador_token = self.consume('OPERADOR')
            derecha = self.parse_expresion_logica_y()
            izquierda = ('OPERACION_LOGICA', operador_token[1], izquierda, derecha)
        return izquierda

    def parse_expresion_logica_y(self):
        izquierda = self.parse_expresion_comparacion()
        while self.current_token and self.current_token[0] == 'OPERADOR' and self.current_token[1] == '&&':
            operador_token = self.consume('OPERADOR')
            derecha = self.parse_expresion_comparacion()
            izquierda = ('OPERACION_LOGICA', operador_token[1], izquierda, derecha)
        return izquierda

    def parse_expresion_comparacion(self):
        izquierda = self.parse_expresion_adicion()
        while self.current_token and self.current_token[0] == 'OPERADOR' and \
              self.current_token[1] in ['==', '!=', '<', '>', '<=', '>=']:
            operador_token = self.consume('OPERADOR')
            derecha = self.parse_expresion_adicion()
            izquierda = ('OPERACION_COMPARACION', operador_token[1], izquierda, derecha)
        return izquierda

    def parse_expresion_adicion(self):
        izquierda = self.parse_expresion_multiplicacion()
        while self.current_token and self.current_token[0] == 'OPERADOR' and \
              self.current_token[1] in ['+', '-']:
            operador_token = self.consume('OPERADOR')
            derecha = self.parse_expresion_multiplicacion()
            izquierda = ('OPERACION_ARITMETICA', operador_token[1], izquierda, derecha)
        return izquierda

    def parse_expresion_multiplicacion(self):
        izquierda = self.parse_expresion_unaria()
        while self.current_token and self.current_token[0] == 'OPERADOR' and \
              self.current_token[1] in ['*', '/', '%']:
            operador_token = self.consume('OPERADOR')
            derecha = self.parse_expresion_unaria()
            izquierda = ('OPERACION_ARITMETICA', operador_token[1], izquierda, derecha)
        return izquierda

    def parse_expresion_unaria(self):
        if self.current_token and self.current_token[0] == 'OPERADOR' and \
           self.current_token[1] in ['-', '!']: # Podría añadir '+' unario si se desea
            operador_token = self.consume('OPERADOR')
            expresion = self.parse_expresion_unaria() # Unarios son asociativos a la derecha (ej. --x)
            return ('OPERACION_UNARIA', operador_token[1], expresion)
        return self.parse_expresion_llamada_o_acceso() # Cambio aquí

    def parse_expresion_llamada_o_acceso(self):
        # Parsea una expresión primaria y luego busca sufijos como ( ), [ ], .
        expr = self.parse_expresion_primaria()

        while self.current_token:
            if self.current_token[0] == 'PARENTESIS' and self.current_token[1] == '(':
                # Llamada a función: expr(...)
                self.consume('PARENTESIS', '(')
                argumentos = []
                while self.current_token and self.current_token[1] != ')':
                    if len(argumentos) > 0:
                        self.consume('COMA')
                    argumentos.append(self.parse_expresion())
                self.consume('PARENTESIS', ')')
                expr = ('LLAMADA', expr, argumentos) # 'expr' es el callee (nombre o expresión que evalúa a función)
            
            elif self.current_token[0] == 'CORCHETE' and self.current_token[1] == '[':
                # Acceso a índice: expr[...]
                self.consume('CORCHETE', '[')
                indice = self.parse_expresion()
                self.consume('CORCHETE', ']')
                expr = ('ACCESO_INDICE', expr, indice)
            
            elif self.current_token[0] == 'PUNTO':
                # Acceso a miembro: expr.identificador
                self.consume('PUNTO')
                miembro_token = self.consume('IDENTIFICADOR')
                expr = ('ACCESO_MIEMBRO', expr, miembro_token[1])
            
            else:
                break # No es un operador de llamada o acceso, terminar
        
        return expr


    def parse_expresion_primaria(self):
        if not self.current_token:
            line, col = (self.tokens[-1][2], self.tokens[-1][3]) if self.tokens else (1,1)
            raise ZiskError("Se esperaba una expresión primaria, pero se encontró el fin del archivo.", line, col)

        token_type, token_value, token_line, token_col = self.current_token

        if token_type == 'IDENTIFICADOR':
            self.consume('IDENTIFICADOR')
            # No chequear si es función o variable aquí, eso es semántico. El parser solo construye el nodo.
            return ('IDENTIFICADOR', token_value)
        
        elif token_type == 'NUMERO':
            self.consume('NUMERO')
            return ('NUMERO', float(token_value) if '.' in token_value else int(token_value))
        
        elif token_type == 'CADENA':
            self.consume('CADENA')
            return ('CADENA', token_value[1:-1]) # Quitar comillas
        
        elif token_type == 'VERDADERO':
            self.consume('VERDADERO')
            return ('BOOLEANO', True)
        
        elif token_type == 'FALSO':
            self.consume('FALSO')
            return ('BOOLEANO', False)
        
        elif token_type == 'NULO':
            self.consume('NULO')
            return ('NULO', None)
        
        elif token_type == 'PARENTESIS' and token_value == '(':
            self.consume('PARENTESIS', '(')
            expresion = self.parse_expresion() # Expresión agrupada
            self.consume('PARENTESIS', ')')
            return expresion # Devuelve la expresión interna, no un nodo 'AGRUPACION'
        
        elif token_type == 'CORCHETE' and token_value == '[':
            return self.parse_lista_literal()
        
        elif token_type == 'LLAVE' and token_value == '{':
            # Podría ser un bloque de código o un objeto literal.
            # Aquí, en el contexto de una expresión, es un objeto literal.
            # Si se quisiera permitir bloques como expresiones (estilo Ruby/Rust), se necesitaría más lógica.
            return self.parse_objeto_literal()
        
        elif token_type == 'ESTE':
            self.consume('ESTE')
            if not self.current_class:
                raise ZiskError("'este' solo puede usarse dentro de un método de clase.", token_line, token_col)
            return ('ESTE',) # Nodo simple para 'este'
        
        elif token_type == 'NUEVO': # 'nuevo Clase(...)'
            self.consume('NUEVO')
            clase_nombre_token = self.consume('IDENTIFICADOR')
            
            self.consume('PARENTESIS', '(')
            argumentos = []
            while self.current_token and self.current_token[1] != ')':
                if len(argumentos) > 0:
                    self.consume('COMA')
                argumentos.append(self.parse_expresion())
            self.consume('PARENTESIS', ')')
            return ('CONSTRUCTOR', clase_nombre_token[1], argumentos)

        elif token_type == 'INGRESAR': # ingresar("prompt") es una expresión que devuelve un valor
            self.consume('INGRESAR')
            self.consume('PARENTESIS', '(')
            prompt_expr = None
            if self.current_token and self.current_token[1] != ')':
                prompt_expr = self.parse_expresion() # El prompt puede ser una expresión
            self.consume('PARENTESIS', ')')
            # No consumir punto y coma aquí, ya que es una expresión.
            # Si se usa como sentencia, parse_sentencia se encargará del punto y coma.
            return ('LLAMADA_NATIVA', 'ingresar', [prompt_expr] if prompt_expr else [])


        else:
            raise ZiskError(f"Expresión primaria no válida: token inesperado '{token_value}' (tipo {token_type})", 
                          token_line, token_col)

    def parse_lista_literal(self):
        self.consume('CORCHETE', '[')
        elementos = []
        while self.current_token and self.current_token[1] != ']':
            if len(elementos) > 0:
                self.consume('COMA')
            elementos.append(self.parse_expresion())
        self.consume('CORCHETE', ']')
        return ('LISTA_LITERAL', elementos)

    def parse_objeto_literal(self):
        self.consume('LLAVE', '{')
        propiedades = [] # Lista de tuplas (clave_str, valor_expr_nodo)
        while self.current_token and self.current_token[1] != '}':
            if len(propiedades) > 0:
                self.consume('COMA')
            
            # Clave puede ser IDENTIFICADOR o CADENA
            clave_token = self.current_token
            if clave_token[0] == 'IDENTIFICADOR':
                self.consume('IDENTIFICADOR')
                clave_str = clave_token[1]
            elif clave_token[0] == 'CADENA':
                self.consume('CADENA')
                clave_str = clave_token[1][1:-1] # Quitar comillas
            else:
                raise ZiskError("Se esperaba un identificador o cadena como clave de objeto.", 
                              clave_token[2], clave_token[3])
            
            self.consume('DOS_PUNTOS')
            valor_expr = self.parse_expresion()
            propiedades.append((clave_str, valor_expr))
        
        self.consume('LLAVE', '}')
        return ('OBJETO_LITERAL', propiedades)

    def parse_si(self):
        self.consume('SI')
        # Podría permitir paréntesis opcionales alrededor de la condición: si (condicion) ...
        condicion = self.parse_expresion()
        
        # 'entonces' es opcional
        if self.current_token and self.current_token[0] == 'ENTONCES':
            self.consume('ENTONCES')
        
        bloque_si = self.parse_bloque_o_sentencia() # Permite bloque {} o sentencia única
        
        bloque_sino = None
        if self.current_token and self.current_token[0] == 'SINO':
            self.consume('SINO')
            bloque_sino = self.parse_bloque_o_sentencia()
        
        return ('SI', condicion, bloque_si, bloque_sino)

    def parse_mientras(self):
        self.consume('MIENTRAS')
        condicion = self.parse_expresion()
        cuerpo = self.parse_bloque_o_sentencia()
        return ('MIENTRAS', condicion, cuerpo)

    def parse_para(self):
        self.consume('PARA')
        self.consume('PARENTESIS', '(')
        
        inicializacion = None
        if self.current_token and self.current_token[0] != 'PUNTO_COMA': # Si no es un punto y coma, hay una inicialización
            if self.current_token[0] == 'VAR': # Puede ser una declaración de var
                inicializacion = self.parse_declaracion_variable() # Ya consume su propio ; opcional
            else: # O una expresión
                inicializacion = self.parse_expresion()
                self.consume('PUNTO_COMA') # ; es obligatorio aquí como separador
        else:
            self.consume('PUNTO_COMA') # ; es obligatorio si no hay inicialización

        condicion = None
        if self.current_token and self.current_token[0] != 'PUNTO_COMA':
            condicion = self.parse_expresion()
        self.consume('PUNTO_COMA') # ; es obligatorio aquí
        
        actualizacion = None
        if self.current_token and self.current_token[1] != ')':
            actualizacion = self.parse_expresion()
        
        self.consume('PARENTESIS', ')')
        
        cuerpo = self.parse_bloque_o_sentencia()
        
        return ('PARA', inicializacion, condicion, actualizacion, cuerpo)


    def parse_hacer_mientras(self):
        self.consume('HACER_MIENTRAS')
        cuerpo = self.parse_bloque_o_sentencia()
        self.consume('MIENTRAS') # Palabra clave 'mientras'
        condicion = self.parse_expresion()
        self.consume_optional_semicolon() # El ; después de la condición es opcional
        return ('HACER_MIENTRAS', cuerpo, condicion)

    def parse_mostrar(self):
        self.consume('MOSTRAR')
        self.consume('PARENTESIS', '(')
        argumentos = []
        while self.current_token and self.current_token[1] != ')':
            if len(argumentos) > 0:
                self.consume('COMA')
            argumentos.append(self.parse_expresion())
        self.consume('PARENTESIS', ')')
        self.consume_optional_semicolon()
        return ('LLAMADA_NATIVA', 'mostrar', argumentos) # Tratado como llamada a función nativa

    # INGRESAR se parsea como una expresión primaria (LLAMADA_NATIVA)
    # def parse_ingresar(self): ... (eliminado, integrado en parse_expresion_primaria)

    def parse_retorna(self):
        start_token = self.consume('RETORNA')
        valor = None
        # Si el siguiente token no es punto y coma (o el fin de un bloque/archivo), entonces hay un valor de retorno
        if self.current_token and not (
            self.current_token[0] == 'PUNTO_COMA' or 
            (self.current_token[0] == 'LLAVE' and self.current_token[1] == '}')) :
            valor = self.parse_expresion()
        self.consume_optional_semicolon()
        return ('RETORNA', valor, (start_token[2],start_token[3]))

    def parse_break(self):
        start_token = self.consume('BREAK')
        self.consume_optional_semicolon()
        return ('BREAK', (start_token[2],start_token[3]))

    def parse_continua(self):
        start_token = self.consume('CONTINUA')
        self.consume_optional_semicolon()
        return ('CONTINUA', (start_token[2],start_token[3]))

    def parse_try_catch(self):
        self.consume('TRY')
        bloque_try = self.parse_bloque() # try siempre espera un bloque {}
        
        bloque_catch = None
        error_var_nombre = None
        if self.current_token and self.current_token[0] == 'CATCH':
            self.consume('CATCH')
            self.consume('PARENTESIS', '(')
            error_var_token = self.consume('IDENTIFICADOR')
            error_var_nombre = error_var_token[1]
            self.consume('PARENTESIS', ')')
            
            self.enter_scope() # Ámbito para la variable de error
            self.current_scope()[error_var_nombre] = ('VAR_ERROR', None) # Asumir tipo 'cualquiera' o 'error'
            bloque_catch = self.parse_bloque() # catch siempre espera un bloque {}
            # self.exit_scope() // Es manejado por parse_bloque
        
        bloque_finally = None
        if self.current_token and self.current_token[0] == 'FINALLY':
            self.consume('FINALLY')
            bloque_finally = self.parse_bloque() # finally siempre espera un bloque {}
        
        return ('TRY_CATCH', bloque_try, error_var_nombre, bloque_catch, bloque_finally)

    def parse_importa(self):
        self.consume('IMPORTA')
        # Por ahora, asumimos que se importa un identificador (que podría ser un nombre de archivo sin extensión)
        # O una cadena para la ruta del archivo.
        # Ejemplo: importa "miModulo"; o importa miModulo;
        # Ejemplo: importa algo desde "miModulo";
        
        elementos_a_importar = [] # Podría ser '*' o lista de identificadores
        path_modulo_str = None
        alias_modulo = None

        # Caso: importa "modulo" [como alias];
        # Caso: importa identificador [como alias]; (identificador es el nombre del modulo)
        # Caso: importa {elem1, elem2} desde "modulo";
        # Caso: importa * desde "modulo";
        
        # Simplificación por ahora: importa ModuloNombreOMRutaString [como Alias];
        if self.current_token[0] == 'CADENA':
            path_token = self.consume('CADENA')
            path_modulo_str = path_token[1][1:-1]
        elif self.current_token[0] == 'IDENTIFICADOR':
            modulo_token = self.consume('IDENTIFICADOR')
            path_modulo_str = modulo_token[1] # Asumir que es el nombre base del módulo
        else:
            raise ZiskError("Se esperaba un nombre de módulo (identificador) o una ruta (cadena) después de 'importa'.",
                          self.current_token[2], self.current_token[3])
        
        # 'desde' no se implementa en esta simplificación. Sería para importar elementos específicos.
        # if self.current_token and self.current_token[0] == 'DESDE':
        #    self.consume('DESDE')
        #    ...

        if self.current_token and self.current_token[0] == 'COMO':
            self.consume('COMO')
            alias_token = self.consume('IDENTIFICADOR')
            alias_modulo = alias_token[1]
        
        self.consume_optional_semicolon()
        # El AST podría ser: ('IMPORTA', path_del_modulo, alias_opcional, lista_de_elementos_especificos)
        return ('IMPORTA', path_modulo_str, alias_modulo)


    def parse_bloque(self, is_function_body=False):
        # Un bloque siempre empieza con '{' y termina con '}'
        # Si is_function_body es true, el enter_scope ya ocurrió para los parámetros.
        # Si no es function body (ej. un bloque if/else/while), creamos un nuevo scope.
        if not is_function_body:
            self.enter_scope()

        self.consume('LLAVE', '{')
        sentencias = []
        while self.current_token and self.current_token[1] != '}':
            sentencias.append(self.parse_declaracion()) # Dentro de un bloque, puede haber declaraciones o sentencias
        self.consume('LLAVE', '}')
        
        self.exit_scope() # Siempre salir del ámbito al final del bloque
        return ('BLOQUE', sentencias)

    def parse_bloque_o_sentencia(self):
        # Usado por if, while, etc., que pueden tener un bloque {} o una única sentencia.
        if self.current_token and self.current_token[0] == 'LLAVE' and self.current_token[1] == '{':
            return self.parse_bloque()
        else:
            # Una única sentencia. Necesita su propio ámbito si introduce variables (ej. var dentro de un if sin llaves)
            # Para simplificar y ser consistente, trataremos una sentencia única como un bloque implícito.
            self.enter_scope()
            sentencia = self.parse_declaracion() # parse_declaracion puede parsear una sentencia
            self.exit_scope()
            return ('BLOQUE', [sentencia]) # Envolver en un nodo BLOQUE

    def peek(self) -> Optional[Tuple[str, str, int, int]]:
        # Devuelve el token actual sin consumirlo (obsoleto, usar self.current_token)
        # Mantenido por si alguna lógica antigua lo usa, pero debería migrarse.
        if self.token_index < len(self.tokens):
            return self.tokens[self.token_index]
        return None

    def consume(self, expected_type: Optional[str] = None, expected_value: Optional[str] = None) -> Tuple[str, str, int, int]:
        token_consumido = self.current_token
        
        if not token_consumido:
            ultimo_token_info = "ninguno (fin de entrada)"
            linea_err, col_err = (self.tokens[-1][2], self.tokens[-1][3] + len(self.tokens[-1][1])) if self.tokens else (1, 1)
            
            expected_info = ""
            if expected_type: expected_info += f"tipo {expected_type}"
            if expected_value:
                if expected_info: expected_info += " "
                expected_info += f"valor '{expected_value}'"
            
            error_msg = f"Se esperaba {expected_info if expected_info else 'un token'} pero se llegó al final del código."
            if self.tokens:
                 error_msg += f" Último token procesado: '{self.tokens[-1][1]}' (tipo {self.tokens[-1][0]}) en línea {self.tokens[-1][2]}, columna {self.tokens[-1][3]}."
            raise ZiskError(error_msg, linea_err, col_err)
            
        token_type, token_value, token_line, token_col = token_consumido
        
        if expected_type and token_type != expected_type:
            raise ZiskError(f"Se esperaba token de tipo {expected_type}, pero se encontró {token_type} ('{token_value}')", 
                          token_line, token_col)
                          
        if expected_value and token_value != expected_value:
            raise ZiskError(f"Se esperaba valor '{expected_value}', pero se encontró '{token_value}'", 
                          token_line, token_col)
        
        self.token_index += 1
        self._actualizar_token_actual() # Actualizar self.current_token                      
        return token_consumido

    def consume_optional_semicolon(self):
        """Consume un punto y coma si está presente. No falla si no lo está."""
        if self.current_token and self.current_token[0] == 'PUNTO_COMA':
            self.consume('PUNTO_COMA')
            return True
        return False

# --- SISTEMA DE TIPOS ---
class ZiskTypeSystem:
    def __init__(self):
        self.type_map = {
            'entero': int,
            'decimal': float,
            'texto': str,
            'booleano': bool,
            'lista': list,
            'objeto': dict, # Objeto literal de Zisk se mapea a dict de Python
            'funcion': type(lambda: None), # Tipo para funciones Zisk (que serán wrappers de Python)
            'clase': type, # Tipo para clases Zisk (que serán clases Python)
            'nulo': type(None)
        }
        # Para el análisis estático y type checking en el parser/compilador
        self.type_annotations: Dict[str, str] = {} # var_name -> tipo_zisk_string
        self.class_hierarchy: Dict[str, Optional[str]] = {} # class_name -> superclass_name
        self.method_signatures: Dict[str, Dict] = {} # "ClassName.methodName" -> {return_type, param_types}

    def check_type(self, value: Any, expected_type_zisk: str, linea: int = 0, col: int = 0) -> bool:
        if expected_type_zisk == 'nulo':
            return value is None
        
        # Manejar tipos de clase Zisk definidos por el usuario
        if expected_type_zisk in self.class_hierarchy: # Es un nombre de clase Zisk
            if isinstance(value, type) and value.__name__ == expected_type_zisk: # Si 'value' es la clase misma
                 return True
            if hasattr(value, '__class__') and value.__class__.__name__ == expected_type_zisk: # Si 'value' es una instancia
                return True
            # Chequear herencia
            current_class = getattr(value, '__class__', None)
            while current_class:
                if current_class.__name__ == expected_type_zisk:
                    return True
                # Para la herencia, necesitaríamos que las clases Zisk hereden de una base o
                # que el type system conozca la jerarquía de clases Python generada.
                # Por ahora, nos basamos en el nombre.
                # Esto se complica si las clases Zisk se mapean a clases Python con nombres diferentes.
                # Asumimos que el nombre de la clase Zisk es el nombre de la clase Python.
                # Si hay herencia, Python `isinstance` podría funcionar mejor si las clases Zisk
                # son subclases de una clase base común o si usamos `isinstance(value, self.classes[expected_type_zisk])`
                # donde self.classes es el dict de clases Zisk del REPL.
                # Esta es una simplificación.
                # Para una herencia robusta, necesitaríamos que `value` sea una instancia de una clase
                # Zisk y chequear `is_subclass_or_same(self.infer_type(value), expected_type_zisk)`
                # Esto requiere que `infer_type` devuelva el nombre de la clase Zisk para instancias.
                break # Simplificación: solo chequeo de nombre exacto o tipo Python mapeado
            # return False # Si no coincide el nombre exacto

        py_type = self.type_map.get(expected_type_zisk)
        if py_type is None: # Tipo Zisk no mapeado a un tipo Python conocido (podría ser una clase definida por el usuario)
            # Aquí es donde el chequeo de clases definidas por el usuario es crucial
            # Si expected_type_zisk es un nombre de clase conocido por el type system (ej. a través de add_class)
            # y 'value' es una instancia de esa clase (o una subclase), debería ser true.
            # Esto es complejo sin el entorno de ejecución. Para el análisis estático, nos fiamos de las anotaciones.
            # En tiempo de ejecución, `isinstance(value, self.repl.classes[expected_type_zisk])` sería lo ideal.
            return False # Por ahora, si no es un tipo base mapeado, y no es un chequeo de clase simple, falla.
            
        return isinstance(value, py_type)

    def infer_type(self, value: Any) -> str:
        if value is None:
            return 'nulo'
        
        # Inferir para instancias de clases Zisk (si es posible)
        if hasattr(value, '__class__') and value.__class__.__name__ in self.class_hierarchy:
            return value.__class__.__name__ # Devuelve el nombre de la clase Zisk

        for type_name, py_type in self.type_map.items():
            if type_name == 'clase' and isinstance(value, type) and value.__name__ in self.class_hierarchy:
                 return 'clase' # Es una clase Zisk
            if isinstance(value, py_type):
                # Excepción: si es un 'dict' pero tenemos una clase Zisk 'objeto', preferir 'objeto'
                if type_name == 'objeto' and isinstance(value, dict): return 'objeto'
                return type_name
        
        return 'desconocido' # O el nombre de la clase Python si no es un tipo Zisk conocido

    def validate_assignment(self, var_name_or_context: str, value: Any, expected_type_zisk: Optional[str], 
                            linea: int = 0, col: int = 0, is_return: bool = False):
        # var_name_or_context puede ser el nombre de una variable, o un contexto como "retorno de función X"
        
        # Si no hay un tipo esperado explícito, no podemos validar (a menos que se infiera del LHS)
        if expected_type_zisk is None:
            return # No hay tipo explícito para validar

        # Si el valor es None (nulo Zisk) y el tipo esperado no es 'nulo' (y no es un tipo que acepte nulo implícitamente)
        # Por ahora, Zisk es estrictamente tipado, así que si el tipo no es 'nulo', un valor nulo no es aceptable
        # a menos que se introduzca el concepto de tipos "opcionales" o "nulables" (ej. texto?)
        if value is None and expected_type_zisk != 'nulo':
            # Podríamos permitir que 'objeto', 'lista', etc., sean nulos si no se inicializan.
            # Por ahora, seamos estrictos.
            # raise ZiskTypeError(
            #     f"No se puede asignar 'nulo' a '{var_name_or_context}' de tipo '{expected_type_zisk}'.",
            #     linea, col
            # )
            pass # Permitir asignar nulo a cualquier tipo por ahora, simplificación. Python lo permite.

        if value is not None and not self.check_type(value, expected_type_zisk, linea, col):
            inferred_type = self.infer_type(value)
            action = "retornar valor" if is_return else "asignar valor"
            raise ZiskTypeError(
                f"Tipos incompatibles: no se puede {action} de tipo '{inferred_type}' "
                f"a '{var_name_or_context}' de tipo '{expected_type_zisk}'.",
                linea, col
            )

    def add_variable_annotation(self, var_name: str, var_type_zisk: Optional[str]):
        if var_type_zisk: # Solo añadir si hay un tipo explícito
            self.type_annotations[var_name] = var_type_zisk

    def get_variable_type(self, var_name: str) -> Optional[str]:
        return self.type_annotations.get(var_name)

    def add_class(self, class_name: str, superclass_name: Optional[str] = None):
        self.class_hierarchy[class_name] = superclass_name
        # Una clase también es un "tipo"
        # self.type_map[class_name] = ... necesitaríamos el objeto clase Python aquí,
        # lo cual es más para tiempo de ejecución.
        # Para análisis estático, class_hierarchy es suficiente.

    def add_method_signature(self, class_name: str, method_name: str, 
                             return_type_zisk: Optional[str] = None, 
                             param_types_zisk: Optional[List[Tuple[str, Optional[str]]]] = None):
        key = f"{class_name}.{method_name}"
        self.method_signatures[key] = {
            'return_type': return_type_zisk,
            'param_types': param_types_zisk or []
        }
    
    def get_method_signature(self, class_name: str, method_name: str) -> Optional[Dict]:
        key = f"{class_name}.{method_name}"
        sig = self.method_signatures.get(key)
        if sig: return sig

        # Intentar buscar en superclases
        current_cls_name = class_name
        while current_cls_name:
            superclass_name = self.class_hierarchy.get(current_cls_name)
            if superclass_name:
                key_super = f"{superclass_name}.{method_name}"
                sig_super = self.method_signatures.get(key_super)
                if sig_super: return sig_super
                current_cls_name = superclass_name
            else:
                break
        return None

    def validate_function_call(self, func_name: str, # O "ClassName.methodName"
                               args: List[Any], # Valores de los argumentos en tiempo de ejecución
                               expected_param_types_zisk: List[Tuple[str, Optional[str]]], # [(nombre, tipo_zisk)]
                               linea: int = 0, col: int = 0):
        
        if len(args) != len(expected_param_types_zisk):
            raise ZiskTypeError(
                f"Función/Método '{func_name}' espera {len(expected_param_types_zisk)} argumentos, "
                f"pero se proporcionaron {len(args)}.",
                linea, col
            )
        
        for i, arg_value in enumerate(args):
            param_name, expected_type = expected_param_types_zisk[i]
            if expected_type: # Si hay anotación de tipo para el parámetro
                self.validate_assignment(f"parámetro '{param_name}' de '{func_name}'", 
                                         arg_value, expected_type, linea, col)
    
    def is_subclass_or_same(self, child_class_name: str, parent_class_name: str) -> bool:
        if child_class_name == parent_class_name:
            return True
        
        current = child_class_name
        visited = {current} # Para evitar ciclos en caso de error en la jerarquía
        
        while current in self.class_hierarchy:
            superclass = self.class_hierarchy[current]
            if superclass == parent_class_name:
                return True
            if superclass is None or superclass in visited : # No más padres o ciclo detectado
                break
            current = superclass
            visited.add(current)
        return False

# --- COMPILADOR (a Python, muy básico) ---
class ZiskCompiler:
    def __init__(self):
        self.indent_level: int = 0
        self.current_class_name: Optional[str] = None # Para saber si estamos dentro de una clase
        self.imported_modules: set[str] = set() # Rastrea módulos importados para evitar duplicados
        # class_method_map: Dict[str, set[str]] = {} # class_name -> set of method_names

    def _indent(self) -> str:
        return " " * self.indent_level * 4

    def compile(self, ast_node: Any) -> str:
        if not ast_node:
            return ""
        
        node_type = ast_node[0]
        # print(f"Compiling: {node_type}") # Debug

        # --- Declaraciones ---
        if node_type == 'PROGRAMA':
            # Añadir importaciones necesarias al principio (ej. para excepciones personalizadas si se usan en Python)
            # O para funciones helper
            python_code = []
            # python_code.append("from zisk_runtime import ZiskList, ZiskObject, ZiskString # etc.")
            for decl in ast_node[1]:
                python_code.append(self.compile(decl))
            return "\n\n".join(filter(None, python_code))

        elif node_type == 'FUNCION':
            # ('FUNCION', nombre, parametros, tipo_retorno, cuerpo_bloque)
            # parametros: List[Tuple[str, Optional[str]]]
            # cuerpo_bloque: ('BLOQUE', sentencias)
            _, nombre, params_list, tipo_ret_zisk, cuerpo_nodo = ast_node
            
            py_params = []
            for p_nombre, p_tipo_zisk in params_list:
                type_hint = f": '{p_tipo_zisk}'" if p_tipo_zisk else "" # Comentario de tipo Zisk
                # Python real type hint sería más complejo de mapear aquí sin el TypeSystem
                py_params.append(f"{p_nombre}{type_hint}")

            py_return_hint = f" # -> {tipo_ret_zisk}" if tipo_ret_zisk else ""

            self.indent_level += 1
            py_cuerpo = self.compile(cuerpo_nodo)
            if not py_cuerpo.strip(): # Si el cuerpo está vacío, Python necesita 'pass'
                 py_cuerpo = self._indent() + "pass"
            self.indent_level -= 1

            return f"{self._indent()}def {nombre}({', '.join(py_params)}){py_return_hint}:\n{py_cuerpo}"

        elif node_type == 'CLASE':
            # ('CLASE', nombre, superclase_nombre, miembros_nodos)
            # miembros_nodos: List[nodos_miembro]
            _, nombre, super_zisk, miembros = ast_node
            
            old_class_name = self.current_class_name
            self.current_class_name = nombre
            
            py_super = f"({super_zisk})" if super_zisk else ""
            
            header = f"{self._indent()}class {nombre}{py_super}:"
            
            self.indent_level += 1
            py_miembros = []
            # Separar campos de métodos para poner campos en __init__ si es necesario,
            # o como atributos de clase si son estáticos.
            # Simplificación: todos los campos como atributos de clase o en __init__ si son de instancia.
            # Por ahora, compilar directamente.
            
            init_fields = []
            class_level_code = []

            for miembro_nodo in miembros:
                m_type = miembro_nodo[0]
                if m_type == 'DECLARACION_VAR_MIEMBRO':
                    # ('DECLARACION_VAR_MIEMBRO', nombre, tipo, valor, es_estatico, es_publico)
                    _, m_nombre, m_tipo, m_valor, m_estatico, _ = miembro_nodo
                    val_str = f" = {self.compile(m_valor)}" if m_valor else ""
                    type_comment = f" # type: {m_tipo}" if m_tipo else ""
                    if m_estatico:
                        class_level_code.append(f"{self._indent()}{m_nombre}{type_comment}{val_str}")
                    else: # Campo de instancia
                        init_fields.append(f"{self._indent()}{self._indent()}self.{m_nombre}{type_comment}{val_str if val_str else ' = None'}")

                elif m_type == 'DECLARACION_CONST_MIEMBRO':
                     # ('DECLARACION_CONST_MIEMBRO', nombre, tipo, valor, es_estatico, es_publico)
                    _, m_nombre, m_tipo, m_valor, _, _ = miembro_nodo # Constantes son implícitamente estáticas
                    val_str = f" = {self.compile(m_valor)}" # Constantes deben tener valor
                    type_comment = f" # type: {m_tipo}" if m_tipo else ""
                    class_level_code.append(f"{self._indent()}{m_nombre}{type_comment}{val_str}")
                
                elif m_type == 'METODO':
                    class_level_code.append(self.compile(miembro_nodo))

            py_init_method = ""
            if init_fields:
                init_body = "\n".join(init_fields) if init_fields else self._indent() + self._indent() + "pass"
                py_init_method = f"{self._indent()}def __init__(self):\n{init_body}"
            
            compiled_miembros = "\n".join(class_level_code)
            if py_init_method:
                 compiled_miembros = py_init_method + "\n" + compiled_miembros

            if not compiled_miembros.strip():
                compiled_miembros = self. _indent() + "pass"

            self.indent_level -= 1
            self.current_class_name = old_class_name
            return f"{header}\n{compiled_miembros}"

        elif node_type == 'METODO':
            # ('METODO', nombre, params, tipo_ret, cuerpo, es_estatico, es_publico)
            _, nombre, params_list, tipo_ret_zisk, cuerpo_nodo, es_estatico, _ = ast_node
            
            py_params = []
            if not es_estatico:
                py_params.append("self")
            
            for p_nombre, p_tipo_zisk in params_list:
                type_hint = f" # type: {p_tipo_zisk}" if p_tipo_zisk else ""
                py_params.append(f"{p_nombre}{type_hint}")
            
            py_return_hint = f" # -> {tipo_ret_zisk}" if tipo_ret_zisk else ""
            
            decorator = ""
            if es_estatico:
                decorator = f"{self._indent()}@staticmethod\n"

            # El nombre del método en Python no necesita cambiar por _privado
            # La convención de _ es suficiente.
            py_method_name = nombre 
            # if not es_publico and not nombre.startswith("_"):
            #    py_method_name = "_" + nombre # Opcional: forzar el _ si es privado

            self.indent_level += 1
            py_cuerpo = self.compile(cuerpo_nodo)
            if not py_cuerpo.strip(): py_cuerpo = self._indent() + "pass"
            self.indent_level -= 1
            
            return f"{decorator}{self._indent()}def {py_method_name}({', '.join(py_params)}){py_return_hint}:\n{py_cuerpo}"

        elif node_type == 'DECLARACION_VAR':
            # ('DECLARACION_VAR', nombre, tipo_zisk, valor_nodo)
            _, nombre, tipo_zisk, valor_nodo = ast_node
            val_str = f" = {self.compile(valor_nodo)}" if valor_nodo is not None else ""
            type_comment = f" # type: {tipo_zisk}" if tipo_zisk else ""
            return f"{self._indent()}{nombre}{type_comment}{val_str}"

        elif node_type == 'DECLARACION_CONST':
            # ('DECLARACION_CONST', nombre, tipo_zisk, valor_nodo)
            _, nombre, tipo_zisk, valor_nodo = ast_node
            val_str = f" = {self.compile(valor_nodo)}" # Constante debe tener valor
            type_comment = f" # type: {tipo_zisk}" if tipo_zisk else ""
            return f"{self._indent()}{nombre}{type_comment}{val_str}"
        
        elif node_type == 'IMPORTA':
            # ('IMPORTA', path_modulo_str, alias_modulo)
            _, path_str, alias = ast_node
            module_name_to_import = path_str.replace(".zk", "") # Asumir que .zk se mapea a .py
            
            if module_name_to_import in self.imported_modules:
                return "" # Ya importado

            self.imported_modules.add(module_name_to_import)
            import_stmt = f"import {module_name_to_import}"
            if alias:
                import_stmt += f" as {alias}"
            return f"{self._indent()}{import_stmt}"

        # --- Sentencias ---
        elif node_type == 'BLOQUE':
            # ('BLOQUE', sentencias_nodos)
            sentencias = ast_node[1]
            if not sentencias: # Bloque vacío
                 # Si el bloque es el cuerpo de una función/método/clase, Python necesita 'pass'
                 # Esto se maneja en el llamador (compile FUNCION, METODO, CLASE, SI, etc.)
                 # Aquí, si es un bloque independiente que resulta vacío, podría ser omitido o 'pass'.
                 # Por ahora, devolvemos las sentencias compiladas. Si están vacías, el string será vacío.
                return "" 
            
            py_sentencias = []
            # No incrementar/decrementar indent_level aquí, el llamador (ej. compile_funcion) lo hace
            # o si es un bloque de if/else, el indent ya está configurado.
            # PERO, si es un bloque suelto, sí necesita indentación.
            # La regla es: el que crea el contexto de indentación (función, if, etc.) lo maneja.
            # parse_bloque crea un ('BLOQUE', ...). Cuando se compila un 'BLOQUE', las sentencias
            # dentro ya deberían estar al nivel de indentación correcto dictado por su contenedor.
            for stmt_nodo in sentencias:
                py_sentencias.append(self.compile(stmt_nodo))
            return "\n".join(filter(None, py_sentencias))


        elif node_type == 'SI':
            # ('SI', condicion_nodo, bloque_si_nodo, bloque_sino_nodo_opcional)
            _, cond_nodo, si_nodo, sino_nodo = ast_node
            py_cond = self.compile(cond_nodo)
            
            header_if = f"{self._indent()}if {py_cond}:"
            self.indent_level += 1
            py_si_bloque = self.compile(si_nodo)
            if not py_si_bloque.strip(): py_si_bloque = self._indent() + "pass"
            self.indent_level -= 1
            
            py_sino_bloque_full = ""
            if sino_nodo:
                header_else = f"{self._indent()}else:"
                self.indent_level += 1
                py_sino_bloque = self.compile(sino_nodo)
                if not py_sino_bloque.strip(): py_sino_bloque = self._indent() + "pass"
                self.indent_level -= 1
                py_sino_bloque_full = f"{header_else}\n{py_sino_bloque}"
            
            return f"{header_if}\n{py_si_bloque}" + (f"\n{py_sino_bloque_full}" if py_sino_bloque_full else "")

        elif node_type == 'MIENTRAS':
            # ('MIENTRAS', condicion_nodo, cuerpo_nodo)
            _, cond_nodo, cuerpo_nodo = ast_node
            py_cond = self.compile(cond_nodo)
            header = f"{self._indent()}while {py_cond}:"
            self.indent_level += 1
            py_cuerpo = self.compile(cuerpo_nodo)
            if not py_cuerpo.strip(): py_cuerpo = self._indent() + "pass"
            self.indent_level -= 1
            return f"{header}\n{py_cuerpo}"

        elif node_type == 'PARA':
            # ('PARA', inicializacion_nodo, condicion_nodo, actualizacion_nodo, cuerpo_nodo)
            _, init_nodo, cond_nodo, update_nodo, cuerpo_nodo = ast_node
            
            py_init = self.compile(init_nodo) if init_nodo else ""
            # La condición por defecto es True si no se especifica
            py_cond = self.compile(cond_nodo) if cond_nodo else "True" 
            py_update = self.compile(update_nodo) if update_nodo else ""

            # Compilación a un bucle while de Python
            # {init}
            # while {cond}:
            #   {cuerpo}
            #   {update}
            
            init_part = f"{py_init}\n" if py_init.strip() else "" # Asegurar indentación correcta si init es multilínea
            
            header_while = f"{self._indent()}while {py_cond}:"
            
            self.indent_level += 1
            py_cuerpo = self.compile(cuerpo_nodo)
            # Si hay actualización, añadirla al final del cuerpo del bucle
            if py_update.strip():
                # Asegurar que py_update tenga la indentación correcta si es multilínea
                # Esto es complejo. Asumimos que py_update es una sola línea o ya está indentado.
                indented_update = "\n".join([f"{self._indent()}{line}" for line in py_update.splitlines()])
                py_cuerpo = (py_cuerpo + "\n" if py_cuerpo.strip() else self._indent() + "pass\n") + indented_update
            elif not py_cuerpo.strip():
                py_cuerpo = self._indent() + "pass"

            self.indent_level -= 1
            
            return f"{init_part}{header_while}\n{py_cuerpo}"


        elif node_type == 'HACER_MIENTRAS':
            # ('HACER_MIENTRAS', cuerpo_nodo, condicion_nodo)
            _, cuerpo_nodo, cond_nodo = ast_node
            py_cond = self.compile(cond_nodo)
            
            # Compila a:
            # while True:
            #   {cuerpo}
            #   if not ({cond}):
            #     break
            header = f"{self._indent()}while True:"
            self.indent_level += 1
            py_cuerpo = self.compile(cuerpo_nodo)
            if_break_cond = f"{self._indent()}if not ({py_cond}):"
            py_break = f"{self._indent()}{self._indent()}break" # Un nivel más de indentación para el break
            
            full_cuerpo = py_cuerpo
            if not full_cuerpo.strip(): # Si el cuerpo original es vacío
                full_cuerpo = self._indent() + "pass"

            self.indent_level -= 1
            return f"{header}\n{full_cuerpo}\n{if_break_cond}\n{py_break}"

        elif node_type == 'RETORNA':
            # ('RETORNA', valor_nodo_opcional, (linea, col))
            _, valor_nodo, _ = ast_node
            py_valor = f" {self.compile(valor_nodo)}" if valor_nodo else ""
            return f"{self._indent()}return{py_valor}"

        elif node_type == 'BREAK':
            return f"{self._indent()}break"
        elif node_type == 'CONTINUA':
            return f"{self._indent()}continue"

        elif node_type == 'TRY_CATCH':
            # ('TRY_CATCH', bloque_try, error_var_nombre, bloque_catch, bloque_finally)
            _, try_b, err_var, catch_b, finally_b = ast_node
            
            header_try = f"{self._indent()}try:"
            self.indent_level += 1
            py_try = self.compile(try_b)
            if not py_try.strip(): py_try = self._indent() + "pass"
            self.indent_level -= 1
            
            py_catch_full = ""
            if catch_b: # Si hay bloque catch
                py_err_var = f" as {err_var}" if err_var else ""
                header_catch = f"{self._indent()}except Exception{py_err_var}:"
                self.indent_level += 1
                py_catch = self.compile(catch_b)
                if not py_catch.strip(): py_catch = self._indent() + "pass"
                self.indent_level -= 1
                py_catch_full = f"\n{header_catch}\n{py_catch}"

            py_finally_full = ""
            if finally_b:
                header_finally = f"{self._indent()}finally:"
                self.indent_level += 1
                py_finally = self.compile(finally_b)
                if not py_finally.strip(): py_finally = self._indent() + "pass"
                self.indent_level -= 1
                py_finally_full = f"\n{header_finally}\n{py_finally}"
            
            return f"{header_try}\n{py_try}{py_catch_full}{py_finally_full}"


        # --- Expresiones (muchas se compilan como sentencias si están solas) ---
        elif node_type == 'ASIGNACION':
            # ('ASIGNACION', operador_str, lhs_nodo, rhs_nodo)
            _, op, lhs_nodo, rhs_nodo = ast_node
            # lhs_nodo puede ser IDENTIFICADOR, ACCESO_MIEMBRO, ACCESO_INDICE
            py_lhs = self.compile(lhs_nodo)
            py_rhs = self.compile(rhs_nodo)
            return f"{self._indent()}{py_lhs} {op} {py_rhs}"

        elif node_type == 'OPERACION_LOGICA' or \
             node_type == 'OPERACION_COMPARACION' or \
             node_type == 'OPERACION_ARITMETICA':
            # ('TIPO_OP', operador_str, lhs_nodo, rhs_nodo)
            _, op, lhs_nodo, rhs_nodo = ast_node
            py_lhs = self.compile(lhs_nodo)
            py_rhs = self.compile(rhs_nodo)
            # Mapear operadores Zisk a Python si son diferentes (ej. && -> and, || -> or)
            py_op = op
            if op == '&&': py_op = 'and'
            if op == '||': py_op = 'or'
            
            # Si es una sentencia (indent > 0), añadir indentación. Si es parte de una expresión más grande, no.
            # Esta función compile() es llamada recursivamente. El _indent() debe ser aplicado
            # solo por la sentencia "raíz" que se está compilando.
            # Decisión: las expresiones devuelven solo su código, la sentencia que las contiene añade indentación.
            # Excepción: si una expresión es una sentencia por sí misma (ej. "a + b;"), debe indentarse.
            # Aquí, asumimos que si se llama directamente a compilar una operación, es parte de algo más grande.
            # Si es una sentencia, parse_sentencia -> parse_expresion -> ... -> compile(operacion)
            # El indentado lo gestiona la llamada a compile que corresponde a una sentencia.
            # Por ejemplo, `DECLARACION_VAR` o `ASIGNACION` añaden `self._indent()`.
            # Si una operación es una "expresión-sentencia", el llamador `parse_sentencia` debería encargarse.
            # Para que esto funcione, una expresión-sentencia en el AST podría ser ('EXPRESION_SENTENCIA', expr_nodo)
            # Y `compile` para `EXPRESION_SENTENCIA` añadiría el indent.
            # O, más simple, si `compile` es llamado para una expresión desde un contexto de sentencia,
            # el indent es añadido por el wrapper.

            # Si esta expresión es la raíz de una sentencia (ej. "a + b;" que no hace nada pero es sintácticamente válido)
            # Necesitamos saber el contexto. Por ahora, las expresiones no se indentan a sí mismas.
            return f"({py_lhs} {py_op} {py_rhs})" # Paréntesis para asegurar precedencia

        elif node_type == 'OPERACION_UNARIA':
            # ('OPERACION_UNARIA', operador_str, operando_nodo)
            _, op, op_nodo = ast_node
            py_op_nodo = self.compile(op_nodo)
            py_op = op
            if op == '!': py_op = 'not ' # 'not' en Python es un operador de palabra clave con espacio
            return f"({py_op}{py_op_nodo})" # Paréntesis

        elif node_type == 'LLAMADA': # Anteriormente LLAMADA_FUNCION
            # ('LLAMADA', callee_nodo, argumentos_nodos_lista)
            _, callee_nodo, args_nodos = ast_node
            py_callee = self.compile(callee_nodo)
            py_args = [self.compile(arg) for arg in args_nodos]
            return f"{py_callee}({', '.join(py_args)})"

        elif node_type == 'LLAMADA_NATIVA':
             # ('LLAMADA_NATIVA', nombre_nativo_str, argumentos_nodos_lista)
            _, nombre_nativo, args_nodos = ast_node
            # Mapear funciones nativas Zisk a funciones Python
            py_func_name = nombre_nativo
            if nombre_nativo == 'mostrar': py_func_name = 'print'
            elif nombre_nativo == 'ingresar': py_func_name = 'input'
            # ... otros mapeos ...

            py_args = [self.compile(arg) for arg in args_nodos if arg is not None]
            
            # Si esta llamada es una sentencia (ej. mostrar(...);), necesita indentación.
            # Asumimos que el llamador de compile (para la sentencia) se encarga de la indentación.
            # Si es parte de una expresión más grande, no se indenta aquí.
            # ¿Cómo saber si es una sentencia? Si su padre es 'PROGRAMA', 'BLOQUE', etc.
            # Esto es complicado. Por ahora, las expresiones no se indentan solas.
            # El compilador de `parse_sentencia` (cuando es una expresión) debe añadir el indent.
            
            # Ejemplo de cómo podría manejarlo si es una sentencia:
            # is_statement_context = ... (necesitaría pasar esta info o inferirla)
            # prefix = self._indent() if is_statement_context else ""
            # return f"{prefix}{py_func_name}({', '.join(py_args)})"
            
            # Devolvemos sin indentación; el contexto de sentencia lo añade.
            call_str = f"{py_func_name}({', '.join(py_args)})"
            # Si el padre es una 'expresion-sentencia', se indentará allí.
            # Hack temporal: si es 'print' o 'input' directo, y es una sentencia, indentar.
            # Esto es incorrecto, el indentado debe ser contextual.
            # La solución correcta es que el nodo 'EXPRESION_SENTENCIA' del parser
            # sea el que añada la indentación al compilar su expresión hija.
            # Si el parser en `parse_sentencia` devuelve ('EXPRESION_SENTENCIA', expr_nodo)
            # if node_type == 'EXPRESION_SENTENCIA':
            #    return f"{self._indent()}{self.compile(ast_node[1])}"
            # Y `parse_sentencia` haría:
            # else:
            #    expr = self.parse_expresion()
            #    self.consume_optional_semicolon()
            #    return ('EXPRESION_SENTENCIA', expr) <-- CAMBIO EN PARSER
            # Por ahora, si es una llamada nativa, es probable que sea una sentencia.
            # Esto es un parche, la solución del parser es mejor.
            current_indent = self._indent() if self.indent_level > 0 or self.current_class_name is None else "" # No indentar si es nivel 0 global
                                                                                                               # excepto si es un print global
            if node_type == 'LLAMADA_NATIVA': # Asumiendo que si se compila directamente es una sentencia
                return f"{current_indent}{call_str}"
            return call_str


        elif node_type == 'CONSTRUCTOR':
            # ('CONSTRUCTOR', nombre_clase_str, argumentos_nodos_lista)
            _, clase_nombre, args_nodos = ast_node
            py_args = [self.compile(arg) for arg in args_nodos]
            return f"{clase_nombre}({', '.join(py_args)})"

        elif node_type == 'ACCESO_MIEMBRO':
            # ('ACCESO_MIEMBRO', objeto_nodo, miembro_nombre_str)
            _, obj_nodo, miembro_str = ast_node
            py_obj = self.compile(obj_nodo)
            return f"{py_obj}.{miembro_str}"

        elif node_type == 'ACCESO_INDICE':
            # ('ACCESO_INDICE', coleccion_nodo, indice_nodo)
            _, coleccion_nodo, indice_nodo = ast_node
            py_coleccion = self.compile(coleccion_nodo)
            py_indice = self.compile(indice_nodo)
            return f"{py_coleccion}[{py_indice}]"
        
        elif node_type == 'IDENTIFICADOR':
            # ('IDENTIFICADOR', nombre_str)
            return ast_node[1]
        
        elif node_type == 'NUMERO': return str(ast_node[1])
        elif node_type == 'CADENA': return f'"{ast_node[1]}"' # Mantener comillas dobles para Python
        elif node_type == 'BOOLEANO': return "True" if ast_node[1] else "False"
        elif node_type == 'NULO': return "None"
        
        elif node_type == 'LISTA_LITERAL':
            # ('LISTA_LITERAL', elementos_nodos_lista)
            elementos_py = [self.compile(e) for e in ast_node[1]]
            return f"[{', '.join(elementos_py)}]"
            
        elif node_type == 'OBJETO_LITERAL':
            # ('OBJETO_LITERAL', propiedades_lista)
            # propiedades_lista: List[Tuple[clave_str, valor_nodo]]
            props_py = []
            for k_str, v_nodo in ast_node[1]:
                props_py.append(f'"{k_str}": {self.compile(v_nodo)}') # Claves como cadenas en Python dict
            return f"{{{', '.join(props_py)}}}"
            
        elif node_type == 'ESTE':
            return "self"
            
        else:
            # Debería haber un token para expresión-sentencia para manejar la indentación correctamente.
            # Si llegamos aquí con un nodo que no es una sentencia completa pero se usa como tal.
            # Por ejemplo, una simple expresión `a + b;`
            # El parser debería envolver esto en ('EXPRESION_SENTENCIA', ('OPERACION_ARITMETICA', ...))
            # Y el compilador para 'EXPRESION_SENTENCIA' añadiría la indentación.
            # Si node_type es una expresión que se está usando como sentencia:
            if isinstance(ast_node, tuple) and len(ast_node) > 1 and isinstance(ast_node[1], (str,int,float,bool,list,dict)):
                 # Es probable una expresión simple usada como sentencia
                 compiled_expr = self._compile_expression_node_as_statement(ast_node)
                 if compiled_expr is not None:
                     return f"{self._indent()}{compiled_expr}"

            print(f"ADVERTENCIA (Compilador): Tipo de nodo AST no manejado explícitamente para compilación a Python: {node_type}")
            return f"{self._indent()}# Nodo no compilado: {ast_node}"

    def _compile_expression_node_as_statement(self, ast_node: Any) -> Optional[str]:
        """Intenta compilar un nodo de expresión que se usa como sentencia."""
        # Esta es una función de ayuda para el caso "else" de arriba, para manejar
        # expresiones que no tienen su propia regla de compilación de sentencia.
        # Esto es un poco un parche; una mejor estructura AST (ej. EXPRESION_SENTENCIA) lo haría más limpio.
        node_type = ast_node[0]
        if node_type in ['OPERACION_LOGICA', 'OPERACION_COMPARACION', 'OPERACION_ARITMETICA', 
                         'OPERACION_UNARIA', 'LLAMADA', 'CONSTRUCTOR', 'ACCESO_MIEMBRO', 
                         'ACCESO_INDICE', 'IDENTIFICADOR', 'NUMERO', 'CADENA', 'BOOLEANO', 
                         'NULO', 'LISTA_LITERAL', 'OBJETO_LITERAL']:
            return self.compile(ast_node) # Re-llama a compile, que devolverá el string de la expresión
        return None


# --- OPTIMIZADOR (muy básico) ---
class ZiskOptimizer:
    def __init__(self):
        self.constant_folding = True
        self.dead_code_elimination = True # Básico (ej. bloques if False)
        # self.inlining = False # Inlining es complejo, desactivado por ahora

    def optimize(self, ast_node: Any) -> Any:
        if not isinstance(ast_node, tuple):
            return ast_node # Literal u otro valor no optimizable directamente aquí

        node_type = ast_node[0]
        
        # Optimizar hijos primero (post-order traversal)
        optimized_children = [node_type]
        for child_node in ast_node[1:]:
            if isinstance(child_node, list): # Lista de nodos (ej. sentencias en un bloque, parámetros)
                optimized_list = [self.optimize(item) for item in child_node]
                # Eliminar Nones de la lista (resultado de optimizaciones como if False)
                optimized_children.append([item for item in optimized_list if item is not None])
            elif isinstance(child_node, tuple) and len(child_node) > 0 and isinstance(child_node[0], str): # Nodo AST hijo
                optimized_children.append(self.optimize(child_node))
            else: # Literal, string, etc.
                optimized_children.append(child_node)
        
        current_node = tuple(optimized_children)

        # --- Plegado de Constantes ---
        if self.constant_folding and node_type == 'OPERACION_ARITMETICA':
            # ('OPERACION_ARITMETICA', op_str, lhs_nodo, rhs_nodo)
            _, op, lhs, rhs = current_node
            if lhs[0] == 'NUMERO' and rhs[0] == 'NUMERO':
                l_val, r_val = lhs[1], rhs[1]
                try:
                    if op == '+': return ('NUMERO', l_val + r_val)
                    if op == '-': return ('NUMERO', l_val - r_val)
                    if op == '*': return ('NUMERO', l_val * r_val)
                    if op == '/': 
                        if r_val == 0: ZiskError("División por cero en plegado de constantes.",0,0) # O dejarlo para runtime
                        return ('NUMERO', l_val / r_val)
                    if op == '%': 
                        if r_val == 0: ZiskError("Módulo por cero en plegado de constantes.",0,0)
                        return ('NUMERO', l_val % r_val)
                except TypeError: # Ej. float + int mezclado de forma rara
                    pass # No se pudo plegar

        # --- Eliminación de Código Muerto (básico) ---
        if self.dead_code_elimination and node_type == 'SI':
            # ('SI', cond_nodo, si_bloque_nodo, sino_bloque_nodo)
            _, cond, si_b, sino_b = current_node
            if cond[0] == 'BOOLEANO':
                if cond[1] is True: # si (verdadero) ...
                    return si_b # Devolver solo el bloque 'si'
                else: # si (falso) ...
                    return sino_b if sino_b else None # Devolver bloque 'sino' o nada
        
        if self.dead_code_elimination and node_type == 'MIENTRAS':
            # ('MIENTRAS', cond_nodo, cuerpo_nodo)
            _, cond, _ = current_node
            if cond[0] == 'BOOLEANO' and cond[1] is False: # mientras (falso) ...
                return None # Eliminar el bucle

        # Más optimizaciones podrían ir aquí (inlining, loop unrolling simplificado, etc.)

        return current_node


# --- REPL y Motor de Ejecución ---
class ZiskREPL:
    def __init__(self, type_system: Optional[ZiskTypeSystem] = None):
        self.lexer = ZiskLexer()
        self.parser = ZiskParser()
        self.optimizer = ZiskOptimizer() # Cada REPL tiene su optimizador
        self.compiler = ZiskCompiler()   # Y su compilador
        
        self.type_system = type_system if type_system else ZiskTypeSystem()
        
        # Estado del REPL (entorno de ejecución)
        self.scopes: List[Dict[str, Any]] = [{}] # Pila de ámbitos para variables en ejecución
        self.functions: Dict[str, Any] = { # Funciones definidas por el usuario
            # Funciones nativas (built-in)
            'mostrar': self._native_mostrar,
            'ingresar': self._native_ingresar,
            'longitud': self._native_longitud,
            'tipo_de': self._native_tipo_de, # 'tipo' es una palabra clave del lenguaje Zisk
            'convertir_a_entero': lambda val: self._native_convertir(val, 'entero'),
            'convertir_a_decimal': lambda val: self._native_convertir(val, 'decimal'),
            'convertir_a_texto': lambda val: self._native_convertir(val, 'texto'),
            'convertir_a_booleano': lambda val: self._native_convertir(val, 'booleano'),
        }
        self.classes: Dict[str, type] = {} # Clases definidas por el usuario (nombre_clase -> objeto_clase_python)
        self.modules: Dict[str, 'ZiskREPL'] = {} # Módulos importados (nombre_modulo -> instancia de ZiskREPL del módulo)
        
        self.current_self: Optional[Any] = None # 'este' en el contexto de un método de instancia
        self.is_in_loop: int = 0 # Contador para anidamiento de bucles (para break/continue)
        self.is_in_function: int = 0 # Contador para anidamiento de funciones (para return)

        # Pasar el type_system al parser si el parser necesita hacer chequeos que dependan de él
        # self.parser.type_system = self.type_system
        # Y al compilador
        # self.compiler.type_system = self.type_system


    # --- Funciones Nativas del REPL ---
    def _native_mostrar(self, *args): print(*args)
    def _native_ingresar(self, prompt: Any = ""):
        if not isinstance(prompt, str):
            prompt = str(prompt) # Asegurar que el prompt sea un string
        try: return input(prompt)
        except EOFError: return self.type_system.type_map['nulo']() # o None

    def _native_longitud(self, collection: Any):
        if isinstance(collection, (str, list, dict)): return len(collection)
        raise ZiskRuntimeError(f"No se puede obtener longitud de un objeto de tipo '{self.type_system.infer_type(collection)}'.")

    def _native_tipo_de(self, value: Any): return self.type_system.infer_type(value)
    
    def _native_convertir(self, value: Any, target_type_zisk: str):
        py_type = self.type_system.type_map.get(target_type_zisk)
        if not py_type:
            raise ZiskRuntimeError(f"Tipo de conversión desconocido: {target_type_zisk}")
        try:
            if target_type_zisk == 'booleano': # bool("False") es True, bool("") es False. Manejo especial.
                if isinstance(value, str):
                    if value.lower() in ["falso", "false", "0", ""]: return False
                    return True # Cualquier otra cadena no vacía es verdadera
                return bool(value)
            return py_type(value)
        except (ValueError, TypeError) as e:
            raise ZiskRuntimeError(f"No se puede convertir '{value}' (tipo {self.type_system.infer_type(value)}) a '{target_type_zisk}': {e}")

    # --- Gestión de Ámbito (Runtime) ---
    def enter_scope(self): self.scopes.append({})
    def exit_scope(self): 
        if len(self.scopes) > 1: self.scopes.pop()
    
    def _get_current_scope(self) -> Dict[str, Any]: return self.scopes[-1]
    
    def _declare_variable(self, name: str, value: Any, tipo_zisk: Optional[str] = None, is_const: bool = False, linea: int = 0, col: int = 0):
        scope = self._get_current_scope()
        if name in scope and scope[name][1]['is_const']: # Chequear si es constante
             raise ZiskRuntimeError(f"No se puede reasignar la constante '{name}'.", linea, col)
        if name in scope and is_const: # Intentando declarar una constante que ya existe como var
             raise ZiskRuntimeError(f"'{name}' ya está declarada como variable, no puede ser redeclarada como constante.", linea, col)

        # Validación de tipo en tiempo de ejecución (si hay tipo explícito)
        if tipo_zisk:
            self.type_system.validate_assignment(name, value, tipo_zisk, linea, col)

        scope[name] = (value, {'is_const': is_const, 'type': tipo_zisk or self.type_system.infer_type(value)})
        # Actualizar también el type_system para análisis estático futuro si es necesario (más para el parser)
        if tipo_zisk:
            self.type_system.add_variable_annotation(name, tipo_zisk)


    def _assign_variable(self, name: str, value: Any, linea: int = 0, col: int = 0):
        for scope in reversed(self.scopes):
            if name in scope:
                if scope[name][1]['is_const']:
                    raise ZiskRuntimeError(f"No se puede reasignar la constante '{name}'.", linea, col)
                
                original_type = scope[name][1]['type']
                if original_type: # Si la variable tenía un tipo declarado o inferido al declarar
                    self.type_system.validate_assignment(name, value, original_type, linea, col)
                
                scope[name] = (value, {'is_const': False, 'type': original_type or self.type_system.infer_type(value)})
                return
        raise ZiskRuntimeError(f"Variable '{name}' no definida.", linea, col)

    def _get_variable_value(self, name: str, linea: int = 0, col: int = 0) -> Any:
        # Buscar en ámbitos de variables
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name][0]
        
        # Buscar en funciones (nativas o definidas)
        if name in self.functions:
            return self.functions[name]
            
        # Buscar en clases
        if name in self.classes:
            return self.classes[name] # Devuelve el objeto clase

        # Buscar en módulos importados (si están en el ámbito global)
        # Esto es más complejo, depende de cómo se manejen los alias de importación.
        # Por ahora, asumimos que los módulos importados están en el ámbito global.
        if name in self.modules: # Si 'name' es un alias de módulo
             return self.modules[name]


        raise ZiskRuntimeError(f"Nombre '{name}' no definido.", linea, col)

    def _get_lvalue_location(self, lhs_node: tuple) -> Tuple[Dict, str, Optional[Any]]:
        """
        Devuelve el 'lugar' donde se asignará un valor:
        (scope_o_objeto, clave_o_nombre_atributo, indice_opcional_para_listas)
        """
        lhs_type, lhs_data = lhs_node[0], lhs_node[1:]
        
        if lhs_type == 'IDENTIFICADOR':
            name = lhs_data[0]
            for scope in reversed(self.scopes):
                if name in scope:
                    return scope, name, None # (ámbito, nombre_variable, no_es_lista_elemento)
            raise ZiskRuntimeError(f"Variable '{name}' no definida para asignación.", lhs_node[2], lhs_node[3]) # Asumiendo que el nodo tiene linea/col

        elif lhs_type == 'ACCESO_MIEMBRO':
            # ('ACCESO_MIEMBRO', objeto_nodo, miembro_nombre_str)
            obj_expr_node, member_name = lhs_data[0], lhs_data[1]
            obj = self.execute(obj_expr_node)
            if isinstance(obj, dict) or hasattr(obj, '__dict__'): # Objeto Zisk (dict) o instancia de clase Python
                return obj, member_name, None # (objeto_o_dict, nombre_atributo, no_es_lista_elemento)
            else:
                raise ZiskRuntimeError(f"No se puede asignar a la propiedad '{member_name}' de un tipo no objetual/diccionario.",0,0) # TODO: linea/col

        elif lhs_type == 'ACCESO_INDICE':
            # ('ACCESO_INDICE', coleccion_nodo, indice_nodo)
            collection_expr_node, index_expr_node = lhs_data[0], lhs_data[1]
            collection = self.execute(collection_expr_node)
            index_val = self.execute(index_expr_node)
            if isinstance(collection, list):
                if not isinstance(index_val, int):
                    raise ZiskTypeError("El índice de la lista debe ser un entero.",0,0)
                # Chequeo de límites se hará en la asignación
                return collection, str(index_val), True # (lista, indice_como_str, es_lista_elemento)
            elif isinstance(collection, dict): # Permitir asignación a dicts con `[]`
                 return collection, str(index_val), False # (dict, clave, no_es_lista_elemento_pero_usa_corchetes)
            else:
                raise ZiskTypeError("Solo se puede usar acceso por índice '[]' en listas o diccionarios.",0,0)
        
        raise ZiskRuntimeError(f"Lado izquierdo de asignación no válido: {lhs_type}",0,0)


    # --- Motor de Ejecución Principal ---
    def execute(self, ast_node: Any) -> Any:
        if ast_node is None: return None # Resultado de optimización (ej. if false)
        
        node_type = ast_node[0]
        # Para obtener linea/col de la sentencia actual, necesitaríamos que el parser los añada a cada nodo AST.
        # Por ahora, muchos errores de runtime no tendrán info precisa de línea/columna.
        # Se podría pasar opcionalmente la tupla del token original al crear el nodo AST.
        # Ejemplo: ('NUMERO', valor, (linea, col))

        linea, col = 0, 0 # Valores por defecto
        if len(ast_node) > 0 and isinstance(ast_node[-1], tuple) and len(ast_node[-1]) == 2 and all(isinstance(i, int) for i in ast_node[-1]):
            # Si el último elemento del nodo AST es una tupla (linea, col)
            # Esto es una convención que podemos adoptar en el parser para algunos nodos
            # linea, col = ast_node[-1]
            pass # No todos los nodos tienen esto, así que no lo extraemos siempre.


        # --- Programa y Bloques ---
        if node_type == 'PROGRAMA':
            result = None
            for stmt_node in ast_node[1]:
                result = self.execute(stmt_node)
                # En el nivel de programa, 'return' no tiene sentido (a menos que sea un script que devuelve un código de salida)
                # 'break' y 'continue' tampoco. El parser debería prohibirlos fuera de bucles/funciones.
            return result # Devuelve el resultado de la última sentencia (comportamiento REPL)

        elif node_type == 'BLOQUE':
            # ('BLOQUE', sentencias_nodos)
            # Un bloque crea su propio ámbito en tiempo de ejecución, manejado por el parser
            # Pero la ejecución del bloque usa los ámbitos del REPL.
            # El parser crea ('BLOQUE', sentencias)
            # Y el enter_scope/exit_scope es llamado por quien parsea el BLOQUE (ej. parse_funcion, parse_si)
            # Aquí, si el bloque es ejecutado, su ámbito ya debería estar activo.
            result = None
            self.enter_scope() # Cada bloque ejecutado tiene su propio ámbito
            try:
                for stmt_node in ast_node[1]:
                    result = self.execute(stmt_node)
                    # Si una sentencia fue un 'return', 'break', 'continue', ya se lanzó la excepción.
            finally:
                self.exit_scope()
            return result # Devuelve el resultado de la última sentencia del bloque


        # --- Declaraciones ---
        elif node_type == 'DECLARACION_VAR':
            # ('DECLARACION_VAR', nombre, tipo_zisk, valor_nodo_opcional)
            _, name, tipo, val_node = ast_node
            value = self.execute(val_node) if val_node else None # O un valor por defecto para el tipo si es null y el tipo no lo permite
            self._declare_variable(name, value, tipo, is_const=False, linea=linea, col=col)
            return value # Una declaración de var podría evaluarse a su valor asignado

        elif node_type == 'DECLARACION_CONST':
            # ('DECLARACION_CONST', nombre, tipo_zisk, valor_nodo)
            _, name, tipo, val_node = ast_node
            if not val_node: raise ZiskRuntimeError("Constante debe ser inicializada.", linea, col)
            value = self.execute(val_node)
            self._declare_variable(name, value, tipo, is_const=True, linea=linea, col=col)
            return value

        elif node_type == 'DECLARACION_VAR_MIEMBRO' or node_type == 'DECLARACION_CONST_MIEMBRO':
            # Se manejan durante la creación de la clase en 'CLASE' o instanciación en 'CONSTRUCTOR'
            # No se ejecutan como sentencias independientes en el flujo normal.
            # Si se llega aquí, es probablemente un error o un AST mal formado.
            # print(f"Advertencia: Ejecutando nodo {node_type} directamente, usualmente manejado por CLASE/CONSTRUCTOR.")
            return None


        elif node_type == 'FUNCION':
            # ('FUNCION', nombre, parametros, tipo_retorno, cuerpo_bloque)
            _, func_name, params_desc, ret_type_zisk, body_node = ast_node
            # params_desc: List[Tuple[str, Optional[str_tipo_zisk]]]
            
            # Aquí 'self' es la instancia de ZiskREPL. No confundir con 'este' de Zisk.
            repl_instance = self 

            def zisk_function_wrapper(*args_values: Any):
                # Guardar estado del REPL para restaurar después de la llamada (recursividad, etc.)
                # old_scopes = [s.copy() for s in repl_instance.scopes] # Copia profunda de ámbitos
                # old_current_self = repl_instance.current_self
                
                # Crear nuevo ámbito para la función
                repl_instance.enter_scope()
                repl_instance.is_in_function += 1
                
                # Vincular argumentos a parámetros en el nuevo ámbito
                if len(args_values) != len(params_desc):
                    raise ZiskRuntimeError(f"Función '{func_name}' esperaba {len(params_desc)} argumentos, recibió {len(args_values)}.",0,0) # TODO: linea/col de llamada
                
                for i, (p_name, p_type_zisk) in enumerate(params_desc):
                    repl_instance._declare_variable(p_name, args_values[i], p_type_zisk, is_const=False) # Parámetros son como 'var'

                return_value = None
                try:
                    # Ejecutar el cuerpo de la función. El cuerpo es un ('BLOQUE', ...)
                    # El 'execute' del BLOQUE ya maneja su propio enter/exit scope, pero
                    # el de la función es el que contiene los parámetros.
                    # Entonces, el execute de BLOQUE debe anidarse correctamente.
                    # El execute('BLOQUE') ya hace enter/exit, así que el enter_scope de la función
                    # es el que contiene los parámetros.
                    self.execute(body_node) # El cuerpo es un 'BLOQUE' que maneja su propio scope interno
                except ReturnException as re:
                    return_value = re.value
                finally:
                    repl_instance.is_in_function -= 1
                    repl_instance.exit_scope() # Salir del ámbito de la función
                    # repl_instance.scopes = old_scopes
                    # repl_instance.current_self = old_current_self
                
                # Validar tipo de retorno
                if ret_type_zisk:
                    self.type_system.validate_assignment(f"retorno de '{func_name}'", return_value, ret_type_zisk, is_return=True) # TODO: linea/col
                
                return return_value

            # Añadir metadatos a la función wrapper para introspección o type checking
            zisk_function_wrapper._zisk_name = func_name
            zisk_function_wrapper._zisk_params = params_desc
            zisk_function_wrapper._zisk_return_type = ret_type_zisk
            
            self.functions[func_name] = zisk_function_wrapper
            self.type_system.add_variable_annotation(func_name, 'funcion') # Anotar que es una función
            return None # La declaración de función no devuelve un valor


        elif node_type == 'CLASE':
            # ('CLASE', nombre, superclase_nombre, miembros_nodos)
            _, class_name_zisk, super_name_zisk, miembros_nodos = ast_node
            
            # Crear el diccionario de atributos para la clase Python
            class_attrs: Dict[str, Any] = {'_zisk_classname': class_name_zisk} 
                                          # '_zisk_fields': {}, '_zisk_methods': {}}
            
            # Campos de instancia (se añadirán al __init__)
            instance_fields_init: List[str] = [] # Código Python para inicializar campos en __init__
            
            # Campos estáticos (atributos de clase)
            # Métodos (estáticos o de instancia)

            for miembro_nodo in miembros_nodos:
                m_type = miembro_nodo[0]
                
                if m_type == 'DECLARACION_VAR_MIEMBRO':
                    # ('DECLARACION_VAR_MIEMBRO', nombre, tipo, valor, es_estatico, es_publico)
                    _, m_name, m_tipo, m_val_nodo, m_estatico, _ = miembro_nodo
                    m_val = self.execute(m_val_nodo) if m_val_nodo else None
                    
                    if m_estatico:
                        class_attrs[m_name] = m_val
                        # Anotación de tipo para el type system (si se accede estáticamente)
                        self.type_system.add_variable_annotation(f"{class_name_zisk}.{m_name}", m_tipo)
                    else: # Campo de instancia
                        # Guardar para el __init__
                        # El valor inicial puede ser una expresión que se evalúa al instanciar.
                        # Necesitamos almacenar el nodo o el valor pre-evaluado.
                        # Si el valor es un literal, podemos usarlo. Si es una expresión compleja,
                        # se complica. Por ahora, asumimos que se evalúa a un valor en la definición.
                        instance_fields_init.append((m_name, m_val, m_tipo))
                        # type_system.add_field_annotation(class_name_zisk, m_name, m_tipo)

                elif m_type == 'DECLARACION_CONST_MIEMBRO':
                    # ('DECLARACION_CONST_MIEMBRO', nombre, tipo, valor_nodo, es_estatico, es_publico)
                    _, m_name, m_tipo, m_val_nodo, _, _ = miembro_nodo
                    m_val = self.execute(m_val_nodo) # Constantes deben tener valor
                    class_attrs[m_name] = m_val # Constantes de clase son como estáticas
                    self.type_system.add_variable_annotation(f"{class_name_zisk}.{m_name}", m_tipo)

                elif m_type == 'METODO':
                    # ('METODO', nombre, params, tipo_ret, cuerpo, es_estatico, es_publico)
                    _, meth_name, meth_params_desc, meth_ret_type, meth_body_node, meth_static, _ = miembro_nodo
                    
                    # Crear el método wrapper (similar a función, pero puede tener 'este')
                    # Necesitamos 'self' de ZiskREPL para acceder a execute, scopes, etc.
                    repl_instance = self

                    def create_method_wrapper(m_name_closure, m_params_desc_closure, m_ret_type_closure, 
                                              m_body_node_closure, m_static_closure, owner_class_name_closure):
                        
                        def zisk_method_wrapper(*args_py: Any): # self_py es la instancia de la clase Python
                            # args_py[0] es 'self_py' (instancia Python) si no es estático
                            # El resto son los argumentos Zisk
                            
                            # old_scopes = [s.copy() for s in repl_instance.scopes]
                            # old_current_self_repl = repl_instance.current_self # Guardar 'este' del REPL

                            self_zisk_instance = None
                            actual_args_zisk = args_py
                            
                            if not m_static_closure:
                                if not args_py: # Debería haber al menos 'self_py'
                                    raise ZiskRuntimeError(f"Método de instancia '{m_name_closure}' llamado incorrectamente (sin 'self' de Python).",0,0)
                                self_zisk_instance = args_py[0] # Este es el 'este' de Zisk
                                actual_args_zisk = args_py[1:]
                            
                            repl_instance.enter_scope()
                            repl_instance.is_in_function +=1 # Métodos son como funciones para return/break/continue

                            # Si es un método de instancia, 'este' está disponible
                            if not m_static_closure:
                                repl_instance.current_self = self_zisk_instance 
                                # repl_instance._declare_variable('este', self_zisk_instance, owner_class_name_closure)
                                # 'este' no se declara, se resuelve a current_self en 'execute' para 'IDENTIFICADOR'->'este'
                                # O, si el parser lo transforma, ('ESTE',) se resuelve a current_self

                            # Vincular argumentos a parámetros
                            if len(actual_args_zisk) != len(m_params_desc_closure):
                                raise ZiskRuntimeError(f"Método '{m_name_closure}' esperaba {len(m_params_desc_closure)} argumentos, recibió {len(actual_args_zisk)}.",0,0)
                            
                            for i, (p_name, p_type_zisk) in enumerate(m_params_desc_closure):
                                repl_instance._declare_variable(p_name, actual_args_zisk[i], p_type_zisk)

                            return_value = None
                            try:
                                repl_instance.execute(m_body_node_closure)
                            except ReturnException as re:
                                return_value = re.value
                            finally:
                                repl_instance.is_in_function -=1
                                repl_instance.exit_scope()
                                # repl_instance.scopes = old_scopes
                                repl_instance.current_self = None # Limpiar 'este' del REPL
                                                             # old_current_self_repl # Restaurar 'este' del REPL

                            if m_ret_type_closure:
                                repl_instance.type_system.validate_assignment(
                                    f"retorno de '{owner_class_name_closure}.{m_name_closure}'",
                                    return_value, m_ret_type_closure, is_return=True)
                            return return_value

                        # Guardar metadatos Zisk en el wrapper Python
                        zisk_method_wrapper._zisk_name = m_name_closure
                        zisk_method_wrapper._zisk_params = m_params_desc_closure
                        zisk_method_wrapper._zisk_return_type = m_ret_type_closure
                        zisk_method_wrapper._zisk_static = m_static_closure

                        if m_static_closure:
                            return staticmethod(zisk_method_wrapper)
                        return zisk_method_wrapper

                    # Crear y añadir el método
                    method_py = create_method_wrapper(meth_name, meth_params_desc, meth_ret_type, 
                                                      meth_body_node, meth_static, class_name_zisk)
                    class_attrs[meth_name] = method_py
                    self.type_system.add_method_signature(class_name_zisk, meth_name, meth_ret_type, meth_params_desc)

            # Crear el __init__ de Python si hay campos de instancia o un constructor Zisk 'constructor'
            # Por ahora, solo campos de instancia. Un método Zisk 'constructor' sería el __init__.
            if instance_fields_init or 'constructor' not in class_attrs : # Si no hay constructor Zisk, crear un __init__ básico
                
                # Capturar 'self' del REPL para usarlo en el __init__ generado
                repl_instance_for_init = self

                def generated_init(self_py, *args_constr): # self_py es la instancia de la clase Python
                    # Inicializar campos de instancia Zisk
                    for f_name, f_val_inicial, f_tipo_zisk in instance_fields_init:
                        # Aquí f_val_inicial ya está evaluado. Si fuera un nodo, se evaluaría aquí.
                        setattr(self_py, f_name, f_val_inicial)
                        # Anotar el tipo del campo en la instancia para el type system en runtime (opcional)
                        # self_py._zisk_field_types[f_name] = f_tipo_zisk

                    # Si hay un método Zisk llamado 'constructor', llamarlo
                    # Esto es si el lenguaje tiene un método especial 'constructor'.
                    # Si 'nuevo Clase()' llama a __init__, y el usuario define 'funcion constructor()',
                    # entonces 'constructor' es un método normal, no el __init__.
                    # Zisk usa 'nuevo Clase()', que en Python es __new__ y __init__.
                    # Si el usuario define `funcion constructor()`, ese sería el inicializador.
                    if 'constructor' in class_attrs and callable(class_attrs['constructor']):
                        # El constructor Zisk es un método normal, se llama con la instancia.
                        # Si el constructor Zisk es estático, no se pasa self_py.
                        # Asumimos que el constructor Zisk es un método de instancia.
                        constructor_zisk = getattr(self_py, 'constructor') # Obtener el método bound
                        constructor_zisk(*args_constr) # Llamar al constructor Zisk

                class_attrs['__init__'] = generated_init
            
            # Determinar clase base Python
            base_classes_py = (object,)
            if super_name_zisk:
                if super_name_zisk in self.classes:
                    base_classes_py = (self.classes[super_name_zisk],)
                else:
                    raise ZiskRuntimeError(f"Clase padre '{super_name_zisk}' no definida.",0,0) # TODO: linea/col
            
            # Crear la clase Python dinámicamente
            try:
                new_class_py = type(class_name_zisk, base_classes_py, class_attrs)
            except Exception as e:
                 raise ZiskRuntimeError(f"Error al crear la clase Python para '{class_name_zisk}': {e}",0,0)


            self.classes[class_name_zisk] = new_class_py
            self.type_system.add_class(class_name_zisk, super_name_zisk)
            return None # Declaración de clase no devuelve valor


        elif node_type == 'IMPORTA':
            # ('IMPORTA', path_modulo_str, alias_modulo_opcional)
            _, module_path_str, alias = ast_node
            
            module_name_eff = alias if alias else module_path_str.split('/')[-1].replace('.zk', '')

            if module_name_eff in self.modules: # Ya importado con este nombre/alias
                return None 

            try:
                # Intentar cargar como archivo .zk
                # Añadir .zk si no está presente y no es una ruta compleja
                file_to_load = module_path_str
                if not module_path_str.endswith(".zk") and '/' not in module_path_str and '\\' not in module_path_str:
                    file_to_load += ".zk"
                
                with open(file_to_load, 'r', encoding='utf-8') as f:
                    module_code = f.read()
                
                # Cada módulo se ejecuta en su propia instancia de REPL (para aislamiento de ámbito global)
                # Compartir el TypeSystem podría ser útil para consistencia entre módulos.
                module_repl = ZiskREPL(type_system=self.type_system) # O un nuevo TypeSystem por módulo
                module_repl.evaluate(module_code, optimize=True) # Ejecutar el código del módulo
                
                self.modules[module_name_eff] = module_repl # Guardar la instancia del REPL del módulo
                # Hacer el módulo accesible en el ámbito global actual del REPL que importa
                self._declare_variable(module_name_eff, module_repl, 'objeto') # Tratar módulo como objeto
                
            except FileNotFoundError:
                raise ZiskRuntimeError(f"No se pudo encontrar el módulo: '{file_to_load}'.", linea, col)
            except Exception as e:
                raise ZiskRuntimeError(f"Error al importar módulo '{module_path_str}': {e}", linea, col)
            return None

        # --- Sentencias de Control de Flujo ---
        elif node_type == 'SI':
            # ('SI', condicion_nodo, bloque_si_nodo, bloque_sino_nodo_opcional)
            _, cond_node, si_node, sino_node = ast_node
            
            # Crear un nuevo ámbito para el bloque 'si' o 'sino' que se ejecute
            # El execute de 'BLOQUE' ya hace esto, así que no es necesario aquí si
            # si_node y sino_node son siempre ('BLOQUE', ...)
            
            if self.execute(cond_node): # Evaluar condición
                return self.execute(si_node)
            elif sino_node:
                return self.execute(sino_node)
            return None

        elif node_type == 'MIENTRAS':
            # ('MIENTRAS', condicion_nodo, cuerpo_nodo)
            _, cond_node, cuerpo_node = ast_node
            self.is_in_loop += 1
            result = None
            try:
                while self.execute(cond_node):
                    try:
                        result = self.execute(cuerpo_node)
                    except ContinueException:
                        continue # Saltar al siguiente ciclo del bucle 'mientras' actual
            except BreakException:
                pass # Salir del bucle 'mientras' actual
            finally:
                self.is_in_loop -= 1
            return result # O el valor de la última iteración si se desea

        elif node_type == 'PARA':
            # ('PARA', inicializacion_nodo, condicion_nodo, actualizacion_nodo, cuerpo_nodo)
            _, init_node, cond_node, update_node, cuerpo_node = ast_node
            
            result = None
            self.enter_scope() # Ámbito para la inicialización del bucle (ej. var i = 0)
            self.is_in_loop += 1
            try:
                if init_node: self.execute(init_node)
                
                # Condición por defecto es verdadero si no se especifica
                while self.execute(cond_node) if cond_node else True:
                    try:
                        result = self.execute(cuerpo_node)
                    except ContinueException:
                        # Antes de continuar, ejecutar la actualización
                        if update_node: self.execute(update_node)
                        continue
                    
                    if update_node: self.execute(update_node) # Actualización al final de cada iteración
            
            except BreakException:
                pass
            finally:
                self.is_in_loop -= 1
                self.exit_scope() # Salir del ámbito del bucle 'para'
            return result


        elif node_type == 'HACER_MIENTRAS':
            # ('HACER_MIENTRAS', cuerpo_nodo, condicion_nodo)
            _, cuerpo_node, cond_node = ast_node
            self.is_in_loop += 1
            result = None
            try:
                while True:
                    try:
                        result = self.execute(cuerpo_node)
                    except ContinueException:
                        # Antes de chequear condición y continuar, ¿debería haber una actualización aquí? No en do-while.
                        if not self.execute(cond_node): break # Si la condición es falsa, salir
                        continue 

                    if not self.execute(cond_node): # Chequear condición al final
                        break
            except BreakException:
                pass
            finally:
                self.is_in_loop -= 1
            return result

        elif node_type == 'RETORNA':
            # ('RETORNA', valor_nodo_opcional, (linea, col))
            if self.is_in_function == 0:
                lc = ast_node[2]
                raise ZiskRuntimeError("'retorna' solo puede usarse dentro de una función o método.", lc[0], lc[1])
            
            val_nodo = ast_node[1]
            return_value = self.execute(val_nodo) if val_nodo else None
            raise ReturnException(return_value)

        elif node_type == 'BREAK':
            if self.is_in_loop == 0:
                lc = ast_node[1]
                raise ZiskRuntimeError("'break' solo puede usarse dentro de un bucle.", lc[0], lc[1])
            raise BreakException()

        elif node_type == 'CONTINUA':
            if self.is_in_loop == 0:
                lc = ast_node[1]
                raise ZiskRuntimeError("'continua' solo puede usarse dentro de un bucle.", lc[0], lc[1])
            raise ContinueException()

        elif node_type == 'TRY_CATCH':
            # ('TRY_CATCH', bloque_try, error_var_nombre_op, bloque_catch_op, bloque_finally_op)
            _, try_b, err_var_name, catch_b, finally_b = ast_node
            result = None
            try:
                result = self.execute(try_b)
            except ReturnException: raise # Propagar si es un return
            except BreakException: raise
            except ContinueException: raise
            except ZiskError as ze: # Capturar errores Zisk (incluye ZiskRuntimeError, ZiskTypeError)
                if catch_b and err_var_name:
                    self.enter_scope()
                    self._declare_variable(err_var_name, ze, 'objeto') # Error es un objeto (o string)
                    try:
                        result = self.execute(catch_b)
                    finally:
                        self.exit_scope()
                else: # No hay catch o no se especifica variable de error, relanzar
                    raise
            except Exception as e: # Capturar otras excepciones Python como errores genéricos
                if catch_b and err_var_name:
                    self.enter_scope()
                    # Convertir la excepción Python a un objeto ZiskError o un string
                    error_obj = ZiskRuntimeError(f"Excepción Python: {type(e).__name__}: {e}",0,0)
                    self._declare_variable(err_var_name, error_obj, 'objeto')
                    try:
                        result = self.execute(catch_b)
                    finally:
                        self.exit_scope()
                else: # No hay catch, relanzar como ZiskRuntimeError
                    raise ZiskRuntimeError(f"Error no capturado: {type(e).__name__}: {e}",0,0) from e
            finally:
                if finally_b:
                    # El resultado de finally no sobrescribe el resultado del try/catch
                    # a menos que finally haga un return/break/continue (que son excepciones)
                    self.execute(finally_b) 
            return result


        # --- Expresiones ---
        elif node_type == 'ASIGNACION':
            # ('ASIGNACION', operador_str, lhs_nodo, rhs_nodo)
            _, op_str, lhs_node_desc, rhs_node_expr = ast_node
            
            # Evaluar el lado derecho primero
            rhs_value = self.execute(rhs_node_expr)
            
            # Obtener la "ubicación" del lado izquierdo
            # Esto es complejo: puede ser variable, propiedad de objeto, elemento de lista.
            # Necesitamos una forma de obtener una referencia al lugar para asignar.
            # location: (objeto_contenedor, clave_o_indice)
            # Ej: para 'a = 1', location = (current_scope, 'a')
            # Ej: para 'obj.x = 1', location = (obj_evaluado, 'x')
            # Ej: para 'lista[0] = 1', location = (lista_evaluada, 0)

            # Esta es una simplificación:
            lvalue_container, key_or_name, is_list_element = self._get_lvalue_location(lhs_node_desc)
            
            current_value = None
            if op_str != '=': # Para '+=', '-=', etc., necesitamos el valor actual
                if is_list_element: # Lista
                    idx = int(key_or_name)
                    if 0 <= idx < len(lvalue_container):
                         current_value = lvalue_container[idx]
                    else:
                         raise ZiskRuntimeError(f"Índice {idx} fuera de rango para la lista.",0,0) #TODO linea/col
                elif isinstance(lvalue_container, dict): # Diccionario o atributo de objeto (si se usa getattr)
                    current_value = lvalue_container.get(key_or_name) if isinstance(lvalue_container, dict) else getattr(lvalue_container, key_or_name, None)
                # Para variables en scope, _get_variable_value las encuentra
                elif isinstance(lvalue_container, dict) and key_or_name in lvalue_container and isinstance(lvalue_container[key_or_name], tuple): # Variable en scope
                    current_value = lvalue_container[key_or_name][0]

                if current_value is None and op_str != '=': # Si es += y la var no existe (o es nulo), error
                     raise ZiskRuntimeError(f"Variable/propiedad '{lhs_node_desc}' no tiene valor inicial para operador '{op_str}'.",0,0)


            # Calcular el nuevo valor para asignación compuesta
            final_value_to_assign = rhs_value
            if op_str == '+=': final_value_to_assign = current_value + rhs_value
            elif op_str == '-=': final_value_to_assign = current_value - rhs_value
            elif op_str == '*=': final_value_to_assign = current_value * rhs_value
            elif op_str == '/=': 
                if rhs_value == 0: raise ZiskRuntimeError("División por cero en asignación.",0,0)
                final_value_to_assign = current_value / rhs_value
            elif op_str == '%=':
                if rhs_value == 0: raise ZiskRuntimeError("Módulo por cero en asignación.",0,0)
                final_value_to_assign = current_value % rhs_value

            # Realizar la asignación
            original_type_of_lvalue = None
            if lhs_node_desc[0] == 'IDENTIFICADOR':
                # Validar tipo antes de la asignación si la variable ya existe y tiene tipo
                for scope_iter in reversed(self.scopes):
                    if key_or_name in scope_iter:
                        original_type_of_lvalue = scope_iter[key_or_name][1]['type']
                        break
                if original_type_of_lvalue:
                    self.type_system.validate_assignment(key_or_name, final_value_to_assign, original_type_of_lvalue, 0,0) #TODO linea/col
                
                lvalue_container[key_or_name] = (final_value_to_assign, {'is_const': False, 'type': original_type_of_lvalue or self.type_system.infer_type(final_value_to_assign)})

            elif is_list_element: # Lista
                idx = int(key_or_name)
                 # Chequear tipo del elemento de la lista si la lista es tipada (característica avanzada)
                if 0 <= idx < len(lvalue_container):
                    lvalue_container[idx] = final_value_to_assign
                elif idx == len(lvalue_container) and op_str == '=': # Permitir añadir si es asignación simple al final
                    lvalue_container.append(final_value_to_assign)
                else:
                    raise ZiskRuntimeError(f"Índice {idx} fuera de rango para asignación a lista.",0,0)
            
            elif isinstance(lvalue_container, dict): # Diccionario (o atributos de objeto si se manejan como dict)
                # Si lvalue_container es un objeto Zisk (instancia de clase Python), usar setattr
                # Aquí asumimos que si no es IDENTIFICADOR ni LISTA, es un objeto/dict.
                # Type checking para campos de objeto
                obj_type_zisk = self.type_system.infer_type(lvalue_container)
                if obj_type_zisk in self.type_system.class_hierarchy: # Es una clase Zisk
                    # Buscar anotación de tipo del campo/propiedad (esto es avanzado)
                    # field_sig = self.type_system.get_field_signature(obj_type_zisk, key_or_name)
                    # if field_sig and field_sig['type']:
                    #    self.type_system.validate_assignment(f"{obj_type_zisk}.{key_or_name}", final_value_to_assign, field_sig['type'], 0,0)
                    pass # Simplificación: no hay chequeo de tipo de campo individual aquí.

                if isinstance(lvalue_container, dict):
                    lvalue_container[key_or_name] = final_value_to_assign
                else: # Asumir que es una instancia de clase Python
                    setattr(lvalue_container, key_or_name, final_value_to_assign)
            
            return final_value_to_assign # Asignación devuelve el valor asignado


        elif node_type == 'OPERACION_ARITMETICA' or \
             node_type == 'OPERACION_COMPARACION' or \
             node_type == 'OPERACION_LOGICA':
            # ('TIPO_OP', operador_str, lhs_nodo, rhs_nodo)
            _, op, lhs_node, rhs_node = ast_node
            
            # Para operadores lógicos de cortocircuito (&&, ||), evaluar lhs primero
            lhs_val = self.execute(lhs_node)

            if node_type == 'OPERACION_LOGICA':
                if op == '&&' and not lhs_val: return False # Cortocircuito
                if op == '||' and lhs_val: return True  # Cortocircuito
            
            rhs_val = self.execute(rhs_node)

            # Chequeo de tipos en runtime (simplificado)
            if node_type == 'OPERACION_ARITMETICA':
                if not (isinstance(lhs_val, (int, float)) and isinstance(rhs_val, (int, float))):
                    # Permitir concatenación de strings con '+'
                    if op == '+' and isinstance(lhs_val, str) and isinstance(rhs_val, str):
                        pass # OK
                    elif op == '*' and ((isinstance(lhs_val, str) and isinstance(rhs_val, int)) or \
                                        (isinstance(lhs_val, int) and isinstance(rhs_val, str))):
                        pass # OK, repetición de string
                    else:
                        raise ZiskTypeError(f"Operación aritmética '{op}' requiere operandos numéricos (o strings para '+', '*') "
                                          f"pero se obtuvieron '{self.type_system.infer_type(lhs_val)}' y "
                                          f"'{self.type_system.infer_type(rhs_val)}'.",0,0) #TODO: linea/col
            
            # Realizar operación
            try:
                if op == '+': return lhs_val + rhs_val
                if op == '-': return lhs_val - rhs_val
                if op == '*': return lhs_val * rhs_val
                if op == '/': 
                    if rhs_val == 0: raise ZiskRuntimeError("División por cero.",0,0)
                    return lhs_val / rhs_val
                if op == '%': 
                    if rhs_val == 0: raise ZiskRuntimeError("Módulo por cero.",0,0)
                    return lhs_val % rhs_val
                
                if op == '==': return lhs_val == rhs_val
                if op == '!=': return lhs_val != rhs_val
                if op == '<': return lhs_val < rhs_val
                if op == '>': return lhs_val > rhs_val
                if op == '<=': return lhs_val <= rhs_val
                if op == '>=': return lhs_val >= rhs_val
                
                # Operadores lógicos ya manejaron cortocircuito, aquí es el resultado final
                if op == '&&': return lhs_val and rhs_val # Python 'and'
                if op == '||': return lhs_val or rhs_val  # Python 'or'
            except TypeError as e:
                raise ZiskTypeError(f"Error de tipo en operación '{op}' con '{self.type_system.infer_type(lhs_val)}' y '{self.type_system.infer_type(rhs_val)}': {e}",0,0)


        elif node_type == 'OPERACION_UNARIA':
            # ('OPERACION_UNARIA', operador_str, operando_nodo)
            _, op, operand_node = ast_node
            operand_val = self.execute(operand_node)
            
            if op == '-':
                if not isinstance(operand_val, (int, float)):
                    raise ZiskTypeError(f"Operador unario '-' requiere operando numérico, no '{self.type_system.infer_type(operand_val)}'.",0,0)
                return -operand_val
            if op == '!': # Negación lógica
                return not operand_val
            # Podría haber '+' unario (identidad numérica)

        elif node_type == 'LLAMADA': # Anteriormente LLAMADA_FUNCION
            # ('LLAMADA', callee_nodo, argumentos_nodos_lista)
            # callee_nodo puede ser IDENTIFICADOR (función global) o ACCESO_MIEMBRO (método)
            _, callee_expr_node, arg_expr_nodes = ast_node
            
            # Evaluar argumentos primero
            arg_values = [self.execute(arg_node) for arg_node in arg_expr_nodes]

            # Evaluar el 'callee'
            # Si callee_expr_node es ('IDENTIFICADOR', 'func_name'), se resuelve a la función.
            # Si es ('ACCESO_MIEMBRO', obj_expr, 'meth_name'), se resuelve al método bound.
            
            callee_val = self.execute(callee_expr_node) # Esto debería devolver un callable (función Python o método bound)

            if not callable(callee_val):
                # Intentar dar un error más específico si es un nombre conocido pero no una función
                name_info = ""
                if callee_expr_node[0] == 'IDENTIFICADOR': name_info = f"'{callee_expr_node[1]}'"
                elif callee_expr_node[0] == 'ACCESO_MIEMBRO': name_info = f"'{self.execute(callee_expr_node[1])}.{callee_expr_node[2]}'"
                
                raise ZiskTypeError(f"El objeto {name_info} (tipo '{self.type_system.infer_type(callee_val)}') no es una función o método llamable.",0,0) #TODO: linea/col

            # Validación de tipos de argumentos y número (si la función/método tiene metadatos Zisk)
            expected_params_desc = getattr(callee_val, '_zisk_params', None)
            if expected_params_desc: # Es una función/método Zisk con metadatos
                # Para métodos de instancia, el 'self' de Python no está en _zisk_params
                # y ya fue manejado por getattr si es un método bound.
                # El número de arg_values debe coincidir con _zisk_params.
                self.type_system.validate_function_call(
                    getattr(callee_val, '_zisk_name', 'desconocido'),
                    arg_values, 
                    expected_params_desc,
                    0,0 # TODO: linea/col de la llamada
                )
            
            try:
                # Si es un método de instancia Python, el 'self' ya está bound por `getattr` en ACCESO_MIEMBRO.
                # Si es una función Zisk, el wrapper maneja el 'self' del REPL.
                # Si es una función nativa, se llama directamente.
                result = callee_val(*arg_values)
            except TypeError as e: # Errores de Python en la llamada (ej. wrong number of args para built-ins)
                if "required positional arguments" in str(e) or "takes" in str(e) and "but" in str(e):
                     raise ZiskRuntimeError(f"Error al llamar a '{getattr(callee_val, '__name__', 'callable')}': {e}",0,0)
                raise # Relanzar otros TypeErrors

            # Validación de tipo de retorno (si hay metadatos Zisk)
            expected_ret_type = getattr(callee_val, '_zisk_return_type', None)
            if expected_ret_type:
                self.type_system.validate_assignment(
                    f"retorno de '{getattr(callee_val, '_zisk_name', 'desconocido')}'",
                    result, expected_ret_type, is_return=True)
            
            return result

        elif node_type == 'LLAMADA_NATIVA':
            # ('LLAMADA_NATIVA', nombre_nativo_str, argumentos_nodos_lista)
            _, native_name, arg_expr_nodes = ast_node
            
            if native_name not in self.functions or not callable(self.functions[native_name]):
                raise ZiskRuntimeError(f"Función nativa '{native_name}' no implementada o no es llamable.",0,0)

            native_func = self.functions[native_name]
            arg_values = [self.execute(arg_node) for arg_node in arg_expr_nodes if arg_node is not None]
            
            # Validación de argumentos para funciones nativas (si tienen metadatos)
            # (Similar a LLAMADA, pero usando self.functions[native_name])
            expected_params_desc = getattr(native_func, '_zisk_params', None)
            if expected_params_desc:
                 self.type_system.validate_function_call(native_name, arg_values, expected_params_desc, 0,0)

            result = native_func(*arg_values)
            
            expected_ret_type = getattr(native_func, '_zisk_return_type', None)
            if expected_ret_type:
                self.type_system.validate_assignment(f"retorno de '{native_name}'", result, expected_ret_type, is_return=True)
            return result


        elif node_type == 'CONSTRUCTOR':
            # ('CONSTRUCTOR', nombre_clase_str, argumentos_nodos_lista)
            _, class_name, arg_expr_nodes = ast_node
            
            if class_name not in self.classes:
                raise ZiskRuntimeError(f"Clase '{class_name}' no definida.",0,0) # TODO: linea/col
            
            target_class_py = self.classes[class_name]
            arg_values = [self.execute(arg_node) for arg_node in arg_expr_nodes]
            
            # Validación de argumentos del constructor (Python __init__ o Zisk 'constructor')
            # Esto es complejo: ¿a qué firma comparamos? Python __init__ o Zisk 'constructor'?
            # Si la clase Zisk tiene un método 'constructor', usar su firma.
            constructor_sig_params = None
            constructor_zisk_method = getattr(target_class_py, 'constructor', None)
            if constructor_zisk_method and hasattr(constructor_zisk_method, '_zisk_params'):
                constructor_sig_params = constructor_zisk_method._zisk_params
            elif hasattr(target_class_py.__init__, '_zisk_params'): # Si __init__ fue generado con metadatos
                constructor_sig_params = target_class_py.__init__._zisk_params

            if constructor_sig_params:
                 self.type_system.validate_function_call(
                    f"constructor de {class_name}", arg_values, constructor_sig_params, 0,0)

            try:
                instance = target_class_py(*arg_values) # Llama a __new__ y luego __init__
            except TypeError as e: # Error en la instanciación de Python (ej. __init__ con #args incorrecto)
                 raise ZiskRuntimeError(f"Error al construir instancia de '{class_name}': {e}",0,0)
            except Exception as e:
                 raise ZiskRuntimeError(f"Excepción inesperada al construir '{class_name}': {e}",0,0)
            
            return instance


        elif node_type == 'ACCESO_MIEMBRO':
            # ('ACCESO_MIEMBRO', objeto_nodo, miembro_nombre_str)
            _, obj_expr_node, member_name = ast_node
            obj_val = self.execute(obj_expr_node)

            # Manejar acceso a miembros de módulos Zisk
            if isinstance(obj_val, ZiskREPL): # Es un módulo Zisk
                # Intentar acceder a una variable, función o clase exportada por el módulo
                # Los ámbitos del módulo están en obj_val.scopes (el global es obj_val.scopes[0])
                # O acceder a sus funciones/clases directamente
                try:
                    return obj_val._get_variable_value(member_name) # Esto busca en scopes, functions, classes del módulo
                except ZiskRuntimeError: # Si no se encuentra en el módulo
                    raise ZiskAttributeError(f"Módulo '{obj_expr_node[1] if obj_expr_node[0]=='IDENTIFICADOR' else 'modulo'}' "
                                          f"no tiene el miembro '{member_name}'.",0,0)


            if isinstance(obj_val, dict):
                if member_name not in obj_val:
                    # Podríamos devolver nulo o lanzar error. Python lanza KeyError.
                    # Para Zisk, un error de atributo es más apropiado.
                    raise ZiskAttributeError(f"Objeto (diccionario) no tiene la propiedad '{member_name}'.",0,0)
                return obj_val[member_name]
            
            if not hasattr(obj_val, member_name):
                obj_type_str = self.type_system.infer_type(obj_val)
                raise ZiskAttributeError(f"Objeto de tipo '{obj_type_str}' no tiene la propiedad '{member_name}'.",0,0)
            
            # getattr puede devolver un valor o un método bound
            attr_val = getattr(obj_val, member_name)
            return attr_val

        elif node_type == 'ACCESO_INDICE':
            # ('ACCESO_INDICE', coleccion_nodo, indice_nodo)
            _, coll_node, idx_node = ast_node
            collection = self.execute(coll_node)
            index = self.execute(idx_node)

            if isinstance(collection, list):
                if not isinstance(index, int):
                    raise ZiskTypeError(f"Índice de lista debe ser entero, no '{self.type_system.infer_type(index)}'.",0,0)
                if not (0 <= index < len(collection)):
                    raise ZiskIndexError(f"Índice {index} fuera de rango para lista de tamaño {len(collection)}.",0,0)
                return collection[index]
            
            elif isinstance(collection, dict):
                # Para diccionarios, el índice es la clave.
                # Python usa __getitem__, que puede lanzar KeyError.
                try:
                    return collection[index] # El índice (clave) puede ser de cualquier tipo hasheable
                except KeyError:
                    raise ZiskKeyError(f"Clave '{index}' no encontrada en el objeto (diccionario).",0,0)
            
            elif isinstance(collection, str): # Permitir indexación de cadenas
                 if not isinstance(index, int):
                    raise ZiskTypeError(f"Índice de texto debe ser entero, no '{self.type_system.infer_type(index)}'.",0,0)
                 if not (0 <= index < len(collection)):
                    raise ZiskIndexError(f"Índice {index} fuera de rango para texto de tamaño {len(collection)}.",0,0)
                 return collection[index]

            else:
                coll_type = self.type_system.infer_type(collection)
                raise ZiskTypeError(f"Tipo '{coll_type}' no soporta acceso por índice '[]'.",0,0)


        # --- Literales y Primitivas ---
        elif node_type == 'IDENTIFICADOR':
            # ('IDENTIFICADOR', nombre_str)
            name = ast_node[1]
            # 'este' es un caso especial, no una variable normal
            # El parser ya debería haberlo convertido a ('ESTE',)
            # if name == 'este': # Esto no debería ocurrir si el parser maneja 'este'
            #     if self.current_self is None:
            #         raise ZiskRuntimeError("'este' no está definido en este contexto (fuera de un método de instancia).",0,0)
            #     return self.current_self
            return self._get_variable_value(name, linea, col)

        elif node_type == 'ESTE':
            # ('ESTE',)
            if self.current_self is None:
                # Este error debería ser capturado por el parser si es posible.
                # Si llega aquí, es un error de lógica en la ejecución.
                raise ZiskRuntimeError("'este' no está definido en el contexto de ejecución actual.",0,0)
            return self.current_self
            
        elif node_type == 'NUMERO': return ast_node[1]
        elif node_type == 'CADENA': return ast_node[1]
        elif node_type == 'BOOLEANO': return ast_node[1]
        elif node_type == 'NULO': return None # Mapeo directo a None de Python
        
        elif node_type == 'LISTA_LITERAL':
            # ('LISTA_LITERAL', elementos_nodos_lista)
            return [self.execute(elem_node) for elem_node in ast_node[1]]
            
        elif node_type == 'OBJETO_LITERAL':
            # ('OBJETO_LITERAL', propiedades_lista)
            # propiedades_lista: List[Tuple[clave_str, valor_nodo]]
            obj_dict = {}
            for key_str, val_node in ast_node[1]:
                obj_dict[key_str] = self.execute(val_node)
            return obj_dict
            
        else:
            raise ZiskRuntimeError(f"Tipo de nodo AST desconocido o no ejecutable: {node_type}",0,0)


    def evaluate(self, code: str, optimize: bool = True):
        """Parsea, opcionalmente optimiza, y ejecuta código Zisk."""
        try:
            tokens = self.lexer.tokenize(code)
            # print("Tokens:", tokens) # Debug
            if not tokens: return None, "" # No hay nada que hacer

            ast = self.parser.parse(tokens)
            # print("AST:", ast) # Debug
            
            if optimize:
                optimized_ast = self.optimizer.optimize(ast)
                # print("Optimized AST:", optimized_ast) # Debug
            else:
                optimized_ast = ast
            
            # Compilar a Python (incluso si no se usa directamente, es bueno tenerlo)
            # El compilador necesita el AST optimizado.
            # El compilador se reinicia para cada evaluación para limpiar su estado (ej. imported_modules)
            current_compiler = ZiskCompiler() 
            # Pasar type_system al compilador si es necesario
            # current_compiler.type_system = self.type_system
            compiled_python = current_compiler.compile(optimized_ast)
            # print("Compiled Python:\n", compiled_python) # Debug

            # Ejecutar el AST (optimizado)
            execution_result = self.execute(optimized_ast)
            
            return execution_result, compiled_python

        except ZiskError as e: # Errores de lexer, parser, type system, runtime
            # Estas excepciones ya deberían tener buena información de línea/columna
            raise # Relanzar para que el REPL o el llamador lo maneje
        except ReturnException as re: # Un 'return' en el nivel superior del REPL
            return re.value, compiled_python # Devolver el valor retornado
        except (BreakException, ContinueException) as bc_err:
            # Estos no deberían escapar de la ejecución de un bucle
            location = "programa principal"
            if self.is_in_loop > 0: location = "un bucle anidado incorrectamente"
            if self.is_in_function > 0: location = "una función/método"

            raise ZiskRuntimeError(f"'{str(bc_err)}' fuera de lugar (en {location}).",0,0)

        # except Exception as e: # Capturar cualquier otra excepción inesperada
        #     # Envolverla en un ZiskError para consistencia, pero es un error interno.
        #     import traceback
        #     tb_str = traceback.format_exc()
        #     # Intentar obtener la última línea/columna del lexer si está disponible
        #     last_line, last_col = self.lexer.linea_actual, self.lexer.columna_actual
        #     raise ZiskError(f"Error interno del intérprete: {type(e).__name__}: {e}\n{tb_str}", last_line, last_col) from e


    def run_repl(self):
        print("Zisk REPL (experimental)")
        print("Escribe ':ayuda' para comandos, ':salir' para terminar.")
        
        buffer_multilinea = []
        prompt = ">>> "

        while True:
            try:
                linea_entrada = input(prompt)
                
                if buffer_multilinea and not linea_entrada.strip(): # Fin de bloque multilínea con línea vacía
                    codigo_completo = "\n".join(buffer_multilinea)
                    buffer_multilinea = []
                    prompt = ">>> "
                elif linea_entrada.strip().startswith(':'): # Comandos del REPL
                    if buffer_multilinea:
                        print("... (entrada multilínea descartada por comando)")
                        buffer_multilinea = []
                    self.handle_repl_command(linea_entrada)
                    prompt = ">>> "
                    continue
                else: # Código normal
                    buffer_multilinea.append(linea_entrada)
                    # Heurística simple para multilínea: si termina con ciertos caracteres o hay bloques abiertos
                    # Una mejor heurística implicaría un mini-parser o chequear balance de paréntesis/llaves.
                    if linea_entrada.strip().endswith(('{', '(', '[', ',', '\\')) or \
                       (not self.lexer.tokenize(linea_entrada)[-1][0] == 'PUNTO_COMA' and \
                        linea_entrada.count('{') > linea_entrada.count('}') or \
                        linea_entrada.count('(') > linea_entrada.count(')') or \
                        linea_entrada.count('[') > linea_entrada.count(']')):
                        prompt = "... "
                        continue
                    else:
                        codigo_completo = "\n".join(buffer_multilinea)
                        buffer_multilinea = []
                        prompt = ">>> "

                if not codigo_completo.strip():
                    continue

                resultado, _ = self.evaluate(codigo_completo) # No nos interesa el python compilado en el REPL
                if resultado is not None:
                    print(repr(resultado)) # Usar repr para mostrar strings con comillas, etc.
                    
            except KeyboardInterrupt:
                if buffer_multilinea:
                    print("\n... (entrada multilínea cancelada)")
                    buffer_multilinea = []
                    prompt = ">>> "
                else:
                    print("\nInterrupción. Usa ':salir' para terminar.")
            except ZiskError as e: # Todos los errores Zisk (lex, parse, type, runtime)
                print(f"\033[91m{e}\033[0m") # Rojo
            except EOFError: # Ctrl+D
                print("\n¡Adiós!")
                break
            except Exception as e: # Errores internos inesperados del REPL
                import traceback
                print(f"\033[91mError interno del REPL: {type(e).__name__}: {e}\033[0m")
                print(traceback.format_exc()) # Para depuración del REPL mismo


    def handle_repl_command(self, comando_linea: str):
        partes = comando_linea.strip().lower().split(maxsplit=1)
        cmd = partes[0]
        arg = partes[1] if len(partes) > 1 else ""

        if cmd == ':salir':
            print("¡Adiós!")
            sys.exit(0)
        elif cmd == ':ayuda':
            print("Comandos especiales del REPL:")
            print("  :ayuda          - Muestra esta ayuda.")
            print("  :salir          - Termina el REPL.")
            print("  :cargar <ruta>  - Carga y ejecuta un archivo .zk.")
            print("  :vars           - Muestra variables globales definidas.")
            print("  :funcs          - Muestra funciones globales definidas.")
            print("  :clases         - Muestra clases globales definidas.")
            print("  :modulos        - Muestra módulos importados.")
            print("  :ast <expr>     - Muestra el AST de la expresión/sentencia (experimental).")
            print("  :tokens <expr>  - Muestra los tokens de la expresión/sentencia (experimental).")
        elif cmd == ':cargar':
            if not arg: print("Uso: :cargar <ruta_del_archivo.zk>")
            else: self.load_and_execute_file(arg)
        elif cmd == ':vars':
            self.show_repl_vars()
        elif cmd == ':funcs':
            self.show_repl_funcs()
        elif cmd == ':clases':
            self.show_repl_clases()
        elif cmd == ':modulos':
            self.show_repl_modules()
        elif cmd == ':ast':
            if not arg: print("Uso: :ast <expresión o sentencia Zisk>")
            else: 
                try:
                    tokens = self.lexer.tokenize(arg)
                    ast = self.parser.parse(tokens)
                    import pprint
                    pprint.pprint(ast)
                except ZiskError as e: print(f"\033[91m{e}\033[0m")
                except Exception as e: print(f"\033[91mError generando AST: {e}\033[0m")
        elif cmd == ':tokens':
            if not arg: print("Uso: :tokens <expresión o sentencia Zisk>")
            else:
                try:
                    tokens = self.lexer.tokenize(arg)
                    import pprint
                    pprint.pprint(tokens)
                except ZiskError as e: print(f"\033[91m{e}\033[0m")
                except Exception as e: print(f"\033[91mError generando tokens: {e}\033[0m")
        else:
            print(f"Comando REPL desconocido: {cmd}")


    def load_and_execute_file(self, filepath: str, optimize_load: bool = True, compile_to_py: bool = True):
        try:
            print(f"Cargando archivo: {filepath}...")
            with open(filepath, 'r', encoding='utf-8') as f:
                file_code = f.read()
            
            # Al cargar un archivo, se ejecuta en el contexto actual del REPL.
            # Si se quisiera aislamiento, se necesitaría una nueva instancia de ZiskREPL.
            resultado, py_code = self.evaluate(file_code, optimize=optimize_load)
            
            if resultado is not None:
                print(f"Resultado de '{filepath}': {repr(resultado)}")

            if compile_to_py and filepath.endswith(".zk"):
                py_filepath = filepath[:-3] + ".py"
                try:
                    with open(py_filepath, 'w', encoding='utf-8') as pyf:
                        pyf.write("# Auto-generado por Zisk Compiler\n\n")
                        pyf.write(py_code)
                    print(f"Compilado a: {py_filepath}")
                except Exception as e_write:
                    print(f"\033[91mError al escribir archivo Python compilado '{py_filepath}': {e_write}\033[0m")

        except FileNotFoundError:
            print(f"\033[91mError: Archivo no encontrado '{filepath}'.\033[0m")
        except ZiskError as e:
            print(f"\033[91mError en archivo '{filepath}': {e}\033[0m")
        except Exception as e:
            import traceback
            print(f"\033[91mError inesperado al cargar '{filepath}': {type(e).__name__}: {e}\033[0m")
            print(traceback.format_exc())

    def show_repl_vars(self):
        print("Variables en el ámbito global:")
        if not self.scopes[0]: print("  (ninguna)")
        for name, (value, meta) in self.scopes[0].items():
            tipo_str = meta.get('type', self.type_system.infer_type(value))
            const_str = " (const)" if meta.get('is_const') else ""
            print(f"  {name}: {tipo_str}{const_str} = {repr(value)}")

    def show_repl_funcs(self):
        print("Funciones definidas (usuario y nativas):")
        user_funcs = {k for k,v in self.functions.items() if hasattr(v, '_zisk_name')}
        native_funcs = {k for k in self.functions if k not in user_funcs}

        if user_funcs:
            print("  Funciones de Usuario:")
            for name in sorted(list(user_funcs)):
                func_obj = self.functions[name]
                params_str = ", ".join([f"{p_name}{': '+p_type if p_type else ''}" 
                                        for p_name, p_type in getattr(func_obj, '_zisk_params', [])])
                ret_str = f" -> {getattr(func_obj, '_zisk_return_type', 'desconocido')}" \
                          if getattr(func_obj, '_zisk_return_type', None) else ""
                print(f"    funcion {name}({params_str}){ret_str}")
        if native_funcs:
            print("  Funciones Nativas:")
            for name in sorted(list(native_funcs)): print(f"    {name}(...)")
        if not self.functions: print("  (ninguna)")
        

    def show_repl_clases(self):
        print("Clases definidas:")
        if not self.classes: print("  (ninguna)")
        for name, klass_obj in self.classes.items():
            super_name = self.type_system.class_hierarchy.get(name)
            super_str = f" extiende {super_name}" if super_name else ""
            print(f"  clase {name}{super_str}")
            # Podríamos listar métodos y campos aquí usando introspección en klass_obj

    def show_repl_modules(self):
        print("Módulos importados:")
        if not self.modules: print("  (ninguno)")
        for name, mod_repl in self.modules.items():
            # mod_repl es una instancia de ZiskREPL
            print(f"  modulo {name} (cargado desde '{getattr(mod_repl, '_source_file', 'desconocido')}')")


# --- Clases de Error de Runtime Específicas de Zisk ---
class ZiskRuntimeError(ZiskError): pass
class ZiskAttributeError(ZiskRuntimeError): pass
class ZiskIndexError(ZiskRuntimeError): pass
class ZiskKeyError(ZiskRuntimeError): pass
# ZiskTypeError ya está definido


if __name__ == "__main__":
    repl = ZiskREPL()
    if len(sys.argv) > 1:
        filepath_arg = sys.argv[1]
        repl.load_and_execute_file(filepath_arg, compile_to_py=True)
    else:
        repl.run_repl()