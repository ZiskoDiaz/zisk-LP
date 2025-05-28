# Documentación del Intérprete y REPL de Zisk

## 1. Introducción

Zisk es un lenguaje de programación interpretado, y este proyecto implementa un intérprete completo junto con un REPL (Read-Eval-Print Loop) para interactuar con él. El sistema está construido en Python 3 y consta de varios componentes clave que trabajan juntos para analizar, (opcionalmente) optimizar, (opcionalmente) compilar a Python, y ejecutar código Zisk.

**Esencialmente, el REPL de Zisk hace lo siguiente:**

1.  **Lee** el código Zisk introducido por el usuario (línea por línea o bloques multilínea).
2.  **Analiza (Evalúa)** este código:
    *   **Lexer (`ZiskLexer`):** Convierte el texto del código en una secuencia de "tokens" (palabras clave, identificadores, números, operadores, etc.).
    *   **Parser (`ZiskParser`):** Toma estos tokens y construye un Árbol de Sintaxis Abstracta (AST), que es una representación estructurada del código.
    *   **Optimizador (`ZiskOptimizer`):** (Opcional) Realiza transformaciones simples en el AST para mejorar su eficiencia (ej. plegado de constantes).
    *   **Motor de Ejecución (parte de `ZiskREPL.execute`):** Recorre el AST y ejecuta las instrucciones, gestionando variables, ámbitos, llamadas a funciones, control de flujo, y operaciones.
    *   **Sistema de Tipos (`ZiskTypeSystem`):** Se utiliza durante la ejecución (y potencialmente en el parsing si se expande) para verificar la compatibilidad de tipos y realizar inferencias.
3.  **Imprime** el resultado de la evaluación (si lo hay) en la consola.
4.  **Repite (Loop)** el proceso, esperando la siguiente entrada del usuario.

Además de la interpretación directa del AST, el sistema también incluye un **Compilador (`ZiskCompiler`)** que puede traducir el AST de Zisk a código Python ejecutable, permitiendo potencialmente la "compilación" de scripts Zisk a Python. El REPL también maneja comandos especiales (ej. `:cargar`, `:ayuda`) para mejorar la interactividad.

## 2. Componentes del Sistema

### 2.1. Excepciones Personalizadas

Zisk define sus propias excepciones para un manejo de errores más específico y claro.

*   **`ZiskError(Exception)`**: Clase base para todos los errores de Zisk. Almacena un mensaje, línea y columna donde ocurrió el error.
    *   **`ZiskTypeError(ZiskError)`**: Para errores relacionados con tipos de datos incompatibles.
    *   **`ZiskRuntimeError(ZiskError)`**: Errores generales que ocurren durante la ejecución del código Zisk.
    *   **`ZiskAttributeError(ZiskRuntimeError)`**: Para accesos a atributos/propiedades inexistentes.
    *   **`ZiskIndexError(ZiskRuntimeError)`**: Para índices fuera de rango en listas o cadenas.
    *   **`ZiskKeyError(ZiskRuntimeError)`**: Para claves no encontradas en objetos/diccionarios.
*   **`BreakException(Exception)`**: Usada internamente para implementar la sentencia `break` en bucles.
*   **`ContinueException(Exception)`**: Usada internamente para implementar la sentencia `continua` en bucles.
*   **`ReturnException(Exception)`**: Usada internamente para implementar la sentencia `retorna` desde funciones/métodos. Almacena el valor a retornar.

### 2.2. `ZiskLexer` (Analizador Léxico)

El lexer es responsable de tomar el código fuente de Zisk como una cadena y dividirlo en una secuencia de tokens.

*   **`__init__(self)`**:
    *   Define `self.tokens_spec`: Una lista de tuplas, donde cada tupla contiene el nombre del tipo de token y una expresión regular para reconocerlo. Las palabras clave están ordenadas por longitud descendente para evitar ambigüedades con prefijos.
    *   Precompila todas las expresiones regulares en un solo patrón para eficiencia.
    *   Inicializa contadores de línea y columna.
*   **`tokenize(self, code: str) -> List[Tuple[str, str, int, int]]`**:
    *   Itera sobre el código de entrada, intentando hacer coincidir los patrones de token en la posición actual.
    *   Ignora comentarios (`COMENTARIO_LINEA`, `COMENTARIO_BLOQUE`) y espacios en blanco (`ESPACIO`).
    *   Si un carácter no coincide con ningún token válido (y no es espacio/comentario), se marca como `NO_VALIDO` y lanza un `ZiskError`.
    *   Devuelve una lista de tuplas, donde cada tupla es `(TIPO_TOKEN, VALOR_TOKEN, NUM_LINEA, NUM_COLUMNA)`.

### 2.3. `ZiskParser` (Analizador Sintáctico)

El parser toma la lista de tokens generada por el lexer y construye un Árbol de Sintaxis Abstracta (AST). El AST es una representación jerárquica de la estructura del código. Utiliza un enfoque de descenso recursivo.

*   **`__init__(self)`**:
    *   Inicializa la lista de tokens, el índice del token actual, y una pila de ámbitos (`self.scopes`) para el análisis semántico básico (verificar declaraciones de variables).
    *   `self.current_class`: Rastrea si el parser está dentro de la definición de una clase.
*   **Métodos de gestión de ámbito (parser)**: `enter_scope`, `exit_scope`, `current_scope`, `variable_declared_in_current_scope`, `variable_declared`.
*   **`parse(self, tokens)`**: Inicia el proceso de parsing.
*   **`parse_programa()`**: Punto de entrada, parsea una secuencia de declaraciones.
*   **`parse_declaracion()`**: Determina si el token actual inicia una función, clase, variable, constante, importación o una sentencia general.
*   **Métodos de parsing específicos**:
    *   `parse_funcion()`: Parsea `funcion nombre(params): tipo_retorno { cuerpo }`.
    *   `parse_clase()`: Parsea `clase Nombre extiende SuperClase { miembros }`.
    *   `parse_declaracion_miembro_clase()`: Parsea atributos de clase.
    *   `parse_metodo_clase()`: Parsea métodos de clase, incluyendo modificadores como `estatico`, `publico`, `privado`.
    *   `parse_declaracion_variable()`: Parsea `var nombre: tipo = valor;`.
    *   `parse_declaracion_constante()`: Parsea `const NOMBRE: tipo = valor;`.
    *   `parse_sentencia()`: Dirige a otros métodos de parsing de sentencias (`parse_si`, `parse_mientras`, etc.) o expresiones.
    *   **Jerarquía de Expresiones (`parse_expresion_...`)**: Un conjunto de métodos para parsear expresiones respetando la precedencia de operadores (asignación, lógicos, comparación, adición, multiplicación, unarios, llamada/acceso, primarios).
        *   `parse_expresion_primaria()`: Parsea los elementos más básicos como literales (números, cadenas, booleanos, nulo), identificadores, expresiones entre paréntesis, `nuevo Clase()`, `este`, `ingresar()`, literales de lista `[]` y objeto `{}`.
    *   `parse_lista_literal()`, `parse_objeto_literal()`.
    *   **Sentencias de Control**: `parse_si()`, `parse_mientras()`, `parse_para()`, `parse_hacer_mientras()`.
    *   **Otras Sentencias**: `parse_mostrar()`, `parse_retorna()`, `parse_break()`, `parse_continua()`, `parse_try_catch()`, `parse_importa()`.
    *   `parse_bloque()`: Parsea un bloque de sentencias encerrado en `{}`. Abre y cierra un nuevo ámbito.
    *   `parse_bloque_o_sentencia()`: Permite que estructuras como `si` o `mientras` tengan un bloque `{}` o una sola sentencia.
*   **`consume(self, expected_type, expected_value)`**: Avanza al siguiente token, verificando opcionalmente su tipo y/o valor. Lanza un error si no coincide.
*   **`consume_optional_semicolon()`**: Consume un punto y coma si está presente.

El AST generado es una estructura de tuplas anidadas, por ejemplo: `('PROGRAMA', [('DECLARACION_VAR', 'x', 'entero', ('NUMERO', 10)), ...])`.

### 2.4. `ZiskTypeSystem` (Sistema de Tipos)

Gestiona la información de tipos, realiza comprobaciones y ayuda en la inferencia de tipos.

*   **`__init__(self)`**:
    *   `self.type_map`: Mapea nombres de tipos de Zisk (`entero`, `texto`, etc.) a tipos de Python (`int`, `str`, etc.).
    *   `self.type_annotations`: Almacena anotaciones de tipo para variables.
    *   `self.class_hierarchy`: Almacena la relación de herencia entre clases de Zisk.
    *   `self.method_signatures`: Almacena las firmas de los métodos (tipos de parámetros y retorno).
*   **`check_type(self, value, expected_type_zisk, ...)`**: Verifica si un valor Python es compatible con un tipo Zisk esperado. Considera clases definidas por el usuario.
*   **`infer_type(self, value)`**: Intenta deducir el tipo Zisk de un valor Python.
*   **`validate_assignment(self, ..., expected_type_zisk, ...)`**: Valida si un valor puede ser asignado a una variable/parámetro/retorno con un tipo Zisk esperado.
*   **`add_variable_annotation(...)`, `get_variable_type(...)`**: Gestiona anotaciones de tipo para variables.
*   **`add_class(...)`, `add_method_signature(...)`, `get_method_signature(...)`**: Registra información sobre clases y métodos para el análisis de tipos.
*   **`validate_function_call(...)`**: Comprueba si los argumentos de una llamada a función coinciden con los tipos esperados de los parámetros.
*   **`is_subclass_or_same(...)`**: Verifica la relación de herencia entre clases Zisk.

### 2.5. `ZiskOptimizer` (Optimizador)

Realiza transformaciones básicas en el AST para mejorar potencialmente el rendimiento o reducir el código.

*   **`__init__(self)`**: Habilita/deshabilita optimizaciones específicas (`constant_folding`, `dead_code_elimination`).
*   **`optimize(self, ast_node)`**:
    *   Recorre el AST (post-orden).
    *   **Plegado de Constantes**: Si encuentra una operación aritmética con operandos literales numéricos (ej. `2 + 3`), la reemplaza por el resultado (`('NUMERO', 5)`).
    *   **Eliminación de Código Muerto**:
        *   Si encuentra `si (verdadero) { ... } sino { ... }`, reemplaza toda la estructura `si` por el bloque del `si`.
        *   Si encuentra `si (falso) { ... } sino { ... }`, reemplaza por el bloque `sino` (o nada si no hay `sino`).
        *   Si encuentra `mientras (falso) { ... }`, elimina el bucle.

### 2.6. `ZiskCompiler` (Compilador a Python)

Traduce el AST de Zisk a código fuente de Python.

*   **`__init__(self)`**: Inicializa el nivel de indentación y el nombre de la clase actual (si aplica). `self.imported_modules` para evitar importaciones duplicadas en el código Python generado.
*   **`_indent(self)`**: Genera la cadena de indentación actual.
*   **`compile(self, ast_node)`**:
    *   Método principal que recibe un nodo del AST y devuelve su representación como código Python.
    *   Utiliza una serie de `if/elif` para manejar cada tipo de nodo del AST (`PROGRAMA`, `FUNCION`, `CLASE`, `ASIGNACION`, `OPERACION_ARITMETICA`, etc.).
    *   Para cada nodo, genera la sintaxis Python equivalente:
        *   `funcion` Zisk -> `def` Python.
        *   `clase` Zisk -> `class` Python (incluyendo herencia y `__init__` para campos de instancia).
        *   Métodos Zisk -> Métodos Python (con `@staticmethod` si es necesario).
        *   `var`, `const` Zisk -> Asignaciones Python.
        *   `importa` Zisk -> `import` Python.
        *   Estructuras de control (`si`, `mientras`, `para`, `hacer_mientras`, `try-catch`) -> Equivalentes en Python.
        *   Operaciones Zisk (`&&`, `||`) -> `and`, `or` Python.
        *   Llamadas a funciones/métodos/constructores Zisk -> Llamadas Python.
        *   Literales Zisk (`nulo`) -> Literales Python (`None`).
    *   Maneja la indentación del código Python generado.
    *   Las llamadas a funciones "nativas" de Zisk como `mostrar` o `ingresar` se traducen a `print` e `input` de Python respectivamente.

### 2.7. `ZiskREPL` (REPL y Motor de Ejecución)

Es el corazón interactivo del intérprete. Gestiona el ciclo de lectura, evaluación e impresión, y también contiene la lógica para ejecutar directamente el AST.

*   **`__init__(self, type_system)`**:
    *   Instancia `ZiskLexer`, `ZiskParser`, `ZiskOptimizer`, `ZiskCompiler`.
    *   Usa una instancia de `ZiskTypeSystem`.
    *   **Estado del REPL (Runtime)**:
        *   `self.scopes`: Pila de ámbitos para almacenar variables en tiempo de ejecución. El primer elemento es el ámbito global.
        *   `self.functions`: Diccionario para funciones definidas por el usuario y funciones nativas (`mostrar`, `ingresar`, `longitud`, `tipo_de`, funciones de conversión).
        *   `self.classes`: Diccionario para clases Zisk definidas por el usuario (mapeadas a clases Python generadas dinámicamente).
        *   `self.modules`: Diccionario para módulos Zisk importados.
        *   `self.current_self`: Almacena la referencia a `este` cuando se ejecuta un método de instancia.
        *   `self.is_in_loop`, `self.is_in_function`: Contadores para validar `break`/`continue`/`retorna`.
*   **Funciones Nativas (`_native_...`)**: Implementaciones Python para las funciones incorporadas de Zisk.
*   **Gestión de Ámbito (Runtime)**: `enter_scope()`, `exit_scope()`, `_get_current_scope()`.
*   **Operaciones de Variables (Runtime)**:
    *   `_declare_variable()`: Añade una variable al ámbito actual, verificando si es constante y validando el tipo con `ZiskTypeSystem`.
    *   `_assign_variable()`: Modifica el valor de una variable existente, verificando si es constante y validando el tipo.
    *   `_get_variable_value()`: Busca y devuelve el valor de una variable, función, clase o módulo.
    *   `_get_lvalue_location()`: Ayuda a determinar dónde se debe asignar un valor (variable, atributo de objeto, elemento de lista).
*   **`execute(self, ast_node)`**:
    *   Este es el **intérprete del AST**. Recorre el árbol nodo por nodo.
    *   Para cada tipo de nodo (`PROGRAMA`, `BLOQUE`, `DECLARACION_VAR`, `FUNCION`, `CLASE`, `SI`, `MIENTRAS`, `ASIGNACION`, `OPERACION_ARITMETICA`, `LLAMADA`, `IDENTIFICADOR`, etc.):
        *   Ejecuta la lógica correspondiente.
        *   **Declaraciones**:
            *   `DECLARACION_VAR`/`CONST`: Evalúa el valor (si hay) y lo declara en el ámbito actual.
            *   `FUNCION`: Crea una función Python wrapper que, al ser llamada, establece un nuevo ámbito, vincula argumentos, ejecuta el cuerpo de la función Zisk y maneja `ReturnException`. Registra esta función en `self.functions`.
            *   `CLASE`: Crea dinámicamente una clase Python. Los métodos Zisk se convierten en métodos Python (wrappers similares a los de función). Los campos de instancia se inicializan en un `__init__` generado. Las constantes y campos estáticos se vuelven atributos de la clase Python. Registra la clase en `self.classes`.
            *   `IMPORTA`: Carga y ejecuta un archivo `.zk` en una nueva instancia de `ZiskREPL` (para aislamiento) y lo hace accesible en el REPL actual.
        *   **Sentencias de Control**:
            *   `SI`: Evalúa la condición y ejecuta el bloque correspondiente.
            *   `MIENTRAS`/`PARA`/`HACER_MIENTRAS`: Ejecutan sus cuerpos iterativamente, manejando `BreakException` y `ContinueException`. `PARA` gestiona su propio ámbito para la variable de inicialización.
            *   `RETORNA`/`BREAK`/`CONTINUA`: Lanzan sus respectivas excepciones para alterar el flujo de control.
            *   `TRY_CATCH`: Ejecuta el bloque `try`. Si ocurre una excepción Zisk (o Python), y hay un bloque `catch` compatible, ejecuta el `catch`. El bloque `finally` se ejecuta siempre.
        *   **Expresiones**:
            *   `ASIGNACION`: Evalúa el lado derecho, determina la ubicación del lado izquierdo y realiza la asignación, incluyendo operaciones compuestas (`+=`, `-=`).
            *   Operaciones (aritméticas, lógicas, comparación, unarias): Evalúan operandos y realizan la operación, con chequeos de tipo básicos en runtime y manejo de cortocircuito para `&&` y `||`.
            *   `LLAMADA`/`LLAMADA_NATIVA`: Evalúa el "llamable" (función/método) y los argumentos, realiza la llamada y devuelve el resultado. Valida tipos de argumentos y retorno si la función/método Zisk tiene metadatos.
            *   `CONSTRUCTOR` (`nuevo Clase(...)`): Busca la clase Python, evalúa argumentos y crea una instancia.
            *   `ACCESO_MIEMBRO` (`obj.miembro`): Evalúa el objeto y devuelve el atributo o método.
            *   `ACCESO_INDICE` (`col[indice]`): Evalúa la colección y el índice, y devuelve el elemento. Soporta listas, diccionarios y cadenas.
            *   Literales (`NUMERO`, `CADENA`, `BOOLEANO`, `NULO`, `LISTA_LITERAL`, `OBJETO_LITERAL`): Devuelven su valor Python correspondiente.
            *   `IDENTIFICADOR`: Busca el valor en los ámbitos.
            *   `ESTE`: Devuelve el valor de `self.current_self`.
*   **`evaluate(self, code: str, optimize: bool = True)`**: Orquesta el proceso: `lex.tokenize -> parser.parse -> optimizer.optimize (opc) -> compiler.compile (info) -> self.execute`.
*   **`run_repl(self)`**: Inicia el bucle interactivo. Maneja entrada multilínea, comandos especiales y errores.
*   **`handle_repl_command(self, comando_linea: str)`**: Procesa comandos como `:salir`, `:ayuda`, `:cargar`, `:vars`, etc.
*   **`load_and_execute_file(self, filepath: str, ...)`**: Carga un archivo `.zk`, lo ejecuta y opcionalmente guarda el código Python compilado.
*   **`show_repl_vars/funcs/clases/modules()`**: Comandos para inspeccionar el estado del REPL.

## 3. Flujo de Ejecución Típico (en el REPL)

1.  Usuario introduce código Zisk.
2.  `ZiskREPL.run_repl()` captura la entrada.
3.  Llama a `ZiskREPL.evaluate(codigo)`.
    a.  `ZiskLexer.tokenize(codigo)` -> `tokens`.
    b.  `ZiskParser.parse(tokens)` -> `ast_original`.
    c.  (Si `optimize` es `True`) `ZiskOptimizer.optimize(ast_original)` -> `ast_optimizado`.
    d.  (Para información o guardado) `ZiskCompiler.compile(ast_optimizado)` -> `codigo_python_compilado`.
    e.  `ZiskREPL.execute(ast_optimizado)` -> `resultado_ejecucion`.
        *   El método `execute` recorre el AST, interactuando con `self.scopes`, `self.functions`, `self.classes`, `ZiskTypeSystem` y lanzando/manejando excepciones de control de flujo.
4.  `ZiskREPL.run_repl()` imprime `resultado_ejecucion` (si no es `None`).
5.  El ciclo se repite.

## 4. Uso

### 4.1. Ejecutar el REPL

```bash
python nombre_del_archivo.py
