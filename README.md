# ✨ Zisk: El Intérprete Alquimista y su REPL Interactivo ✨

## 🚀 ¡Bienvenido al Mundo de Zisk!

Zisk no es solo otro lenguaje; ¡es una aventura en la creación de lenguajes! Este proyecto te presenta un intérprete completo para Zisk, acompañado de un REPL (Bucle de Leer-Evaluar-Imprimir) para que puedas conversar directamente con tu código. Forjado en Python 3, Zisk es un ecosistema de componentes que colaboran armoniosamente para dar vida a tus scripts.

> **En Esencia, el REPL de Zisk es como un Mago que:**
>
> 1.  📜 **Escucha Atentamente (Lee):** Captura tus encantamientos Zisk, ya sean líneas sueltas o poderosos bloques de código.
> 2.  🔮 **Descifra y Transforma (Evalúa):**
>     *   🔍 **El Ojo del Lexer (`ZiskLexer`):** Como un escriba meticuloso, descompone tu texto en "glifos" (tokens): palabras clave, nombres arcanos, números místicos, y símbolos de poder.
>     *   🌳 **El Arquitecto del Parser (`ZiskParser`):** Con los glifos, erige un Árbol de Sintaxis Abstracta (AST), el esqueleto estructural de tu hechizo.
>     *   ✨ **El Toque del Optimizador (`ZiskOptimizer`):** (Opcional) Como un alquimista refinando metales, pule el AST para mejorar su esencia (ej. transformando `2+2` en `4`).
>     *   🌪️ **El Núcleo de Ejecución (en `ZiskREPL.execute`):** El corazón del motor, que recorre el AST, conjurando variables, tejiendo flujos de control, y desatando operaciones.
>     *   ⚖️ **El Guardián de Tipos (`ZiskTypeSystem`):** Un sabio que vela por la armonía de los tipos de datos, tanto en la ejecución como, potencialmente, en la creación del hechizo.
> 3.  💬 **Revela el Resultado (Imprime):** Muestra en tu esfera de adivinación (la consola) el fruto de tu conjuro.
> 4.  🔄 **Espera Nuevas Órdenes (Bucle):** El ciclo se reinicia, listo para tu siguiente instrucción.

Y como si fuera poco, Zisk cuenta con un **Compilador (`ZiskCompiler`)** capaz de transmutar tus encantamientos Zisk en escrituras Python, ¡abriendo portales a otras dimensiones de ejecución! El REPL también es tu grimorio personal, con comandos mágicos (como `:cargar` y `:ayuda`) para una experiencia más fluida.

---

## 🧩 Los Bloques Constructores: Componentes del Sistema

<details>
<summary>🚨 <strong>Guardianes del Error: Excepciones Personalizadas</strong></summary>

Zisk blande sus propias espadas contra los errores, ofreciendo claridad en el caos.

*   **`ZiskError(Exception)`**: El general de todos los errores Zisk. Porta el mensaje, la línea y columna del incidente.
    *   **`ZiskTypeError(ZiskError)`**: Surge cuando los elementos no encajan (tipos incompatibles).
    *   **`ZiskRuntimeError(ZiskError)`**: El grito de batalla para problemas durante la ejecución.
    *   **`ZiskAttributeError(ZiskRuntimeError)`**: Cuando buscas un tesoro que no existe (atributo/propiedad faltante).
    *   **`ZiskIndexError(ZiskRuntimeError)`**: Si te aventuras más allá de los límites conocidos (índice fuera de rango).
    *   **`ZiskKeyError(ZiskRuntimeError)`**: Cuando la llave no abre ninguna cerradura (clave no encontrada).
*   **`BreakException(Exception)`**: El hechizo de escape de bucles (`break`).
*   **`ContinueException(Exception)`**: El salto temporal dentro de bucles (`continua`).
*   **`ReturnException(Exception)`**: El portal de salida de funciones/métodos (`retorna`), llevando consigo el botín (valor).
</details>

<details>
<summary>🔍 <strong>El Escriba: `ZiskLexer` (Analizador Léxico)</strong></summary>

El Lexer es el primer contacto, transformando el frío texto en una danza de tokens.

*   **`__init__(self)`**:
    *   Define `self.tokens_spec`: Un pergamino con las runas (expresiones regulares) para cada tipo de token. Las palabras de poder (keywords) se ordenan por su grandeza para evitar confusiones.
    *   Prepara los conjuros (expresiones regulares compiladas) para una rápida invocación.
*   **`tokenize(self, code: str) -> List[Tuple[str, str, int, int]]`**:
    *   Recorre el código, identificando tokens uno por uno.
    *   Los susurros (comentarios) y el aliento (espacios) son etéreos y se ignoran.
    *   Un carácter rebelde que no encaje en ningún token conocido (`NO_VALIDO`) desata un `ZiskError`.
    *   Devuelve una procesión de tokens: `(TIPO_TOKEN, VALOR_TOKEN, NUM_LINEA, NUM_COLUMNA)`.
</details>

<details>
<summary>🌳 <strong>El Cartógrafo: `ZiskParser` (Analizador Sintáctico)</strong></summary>

El Parser toma los tokens y dibuja el mapa del código: el Árbol de Sintaxis Abstracta (AST).

*   **`__init__(self)`**:
    *   Prepara su mesa de trabajo: la lista de tokens, un puntero al token actual, y una pila de esferas de influencia (`self.scopes`) para rastrear la existencia de nombres.
    *   `self.current_class`: Un faro que indica si se está trazando el plano de una `clase`.
*   **Métodos de Ámbito (Parser)**: `enter_scope`, `exit_scope`, etc., para saber qué nombres son visibles.
*   **`parse(self, tokens)`**: El inicio de la cartografía.
*   **`parse_programa()`**: El mapa general, compuesto de múltiples regiones (declaraciones).
*   **`parse_declaracion()`**: Identifica si la región actual es una `funcion`, `clase`, `var`, `const`, `importa` o una acción (sentencia).
*   **Planos Detallados**:
    *   `parse_funcion()`: Dibuja `funcion nombre(params): tipo_retorno { cuerpo }`.
    *   `parse_clase()`: Esboza `clase Nombre extiende SuperClase { miembros }`.
    *   ...y muchos más para cada estructura del lenguaje, incluyendo la **Jerarquía de Expresiones** que respeta el orden de las operaciones matemáticas y lógicas.
    *   `parse_expresion_primaria()`: Los elementos fundamentales: números, textos, `verdadero`/`falso`, `nulo`, `(expresiones)`, `nuevo Clase()`, `este`, `ingresar()`, `[]` (listas), y `{}` (objetos).
*   **`consume(self, ...)`**: Avanza al siguiente token, asegurándose de que es el esperado.
*   **El AST resultante**: Una estructura de tuplas anidadas, como un árbol genealógico del código. Ej: `('PROGRAMA', [('DECLARACION_VAR', 'x', 'entero', ('NUMERO', 10))])`.
</details>

<details>
<summary>⚖️ <strong>El Oráculo de Tipos: `ZiskTypeSystem`</strong></summary>

Vigila la pureza y compatibilidad de los tipos de datos en el reino de Zisk.

*   **`__init__(self)`**:
    *   `self.type_map`: Un diccionario que traduce los nombres de tipos Zisk (`entero`) a sus contrapartes Python (`int`).
    *   Registros para anotaciones de tipo, jerarquías de clases y firmas de métodos.
*   **`check_type(...)`**: Comprueba si un valor terrenal (Python) se alinea con un tipo celestial Zisk.
*   **`infer_type(...)`**: Intenta adivinar el tipo Zisk de un valor.
*   **`validate_assignment(...)`**: Dictamina si un valor puede ser confiado a una variable o parámetro de un tipo específico.
*   Y más métodos para registrar y consultar información de tipos de clases, métodos y variables.
</details>

<details>
<summary>✨ <strong>El Refinador: `ZiskOptimizer` (Optimizador)</strong></summary>

Un artesano que pule el AST, buscando la eficiencia y eliminando lo superfluo.

*   **`__init__(self)`**: Permite activar o desactivar ciertos refinamientos.
*   **`optimize(self, ast_node)`**:
    *   Recorre el AST.
    *   **Alquimia de Constantes**: Transforma `3 + 7` directamente en `('NUMERO', 10)`.
    *   **Poda de Ramas Muertas**: Si ve `si (falso) { ... }`, elimina esa rama del árbol.
</details>

<details>
<summary>🐍 <strong>El Traductor Interdimensional: `ZiskCompiler` (Compilador a Python)</strong></summary>

Este erudito traduce los encantamientos Zisk, representados por el AST, al lenguaje de las serpientes (Python).

*   **`__init__(self)`**: Prepara su pluma y pergamino (nivel de indentación, etc.).
*   **`compile(self, ast_node)`**:
    *   Toma un nodo del AST y devuelve su forma en Python.
    *   Una vasta biblioteca de `if/elif` traduce cada estructura Zisk:
        *   `funcion` Zisk ➡️ `def` Python.
        *   `clase` Zisk ➡️ `class` Python (con `__init__` y herencia).
        *   `mostrar("hola")` ➡️ `print("hola")`.
        *   `&&`, `||` ➡️ `and`, `or`.
    *   Maneja la indentación para que el código Python sea legible y funcional.
    *   El resultado es un string que contiene código Python listo para ser invocado.
    ```python
    # Ejemplo de salida del compilador
    def mi_funcion_zisk(parametro_zisk): # type: entero
        # -> texto
        x = 10 # type: entero
        if x > 5:
            return "mayor"
        else:
            return "menor o igual"
    ```
</details>

<details>
<summary>🎩 <strong>El Director de Orquesta: `ZiskREPL` (REPL y Motor de Ejecución)</strong></summary>

El `ZiskREPL` es el maestro de ceremonias, dirigiendo la interpretación del código Zisk y permitiendo la interacción directa.

*   **`__init__(self, ...)`**:
    *   Ensambla a todos los demás artesanos: `ZiskLexer`, `ZiskParser`, etc.
    *   **Cámara de los Secretos (Estado del REPL en Runtime)**:
        *   `self.scopes`: Una torre de esferas de memoria (ámbitos) donde residen las variables.
        *   `self.functions`: Un grimorio de funciones, tanto las nativas de Zisk (`mostrar`) como las creadas por el usuario.
        *   `self.classes`: Un bestiario de clases Zisk (transformadas en clases Python).
        *   `self.modules`: Un atlas de mundos importados (módulos Zisk).
        *   `self.current_self`: El reflejo de `este` en el espejo de los métodos de instancia.
*   **Invocaciones Nativas (`_native_...`)**: Los hechizos básicos que Zisk conoce desde su nacimiento (`mostrar`, `ingresar`, `longitud`).
*   **Custodia de Variables (Runtime)**: Métodos para declarar, asignar y recuperar el valor de las variables, respetando sus tipos y si son constantes.
*   **`execute(self, ast_node)`**: ¡La ejecución en sí misma!
    *   Este es el **intérprete del AST**. Viaja a través del árbol, nodo por nodo.
    *   Para cada tipo de nodo (`PROGRAMA`, `FUNCION`, `CLASE`, `SI`, `ASIGNACION`, `LLAMADA`, etc.):
        *   **Declaraciones**:
            *   `FUNCION`: Envuelve el cuerpo Zisk en una función Python, manejando ámbitos y el retorno.
            *   `CLASE`: Esculpe una clase Python dinámicamente, con sus métodos y atributos.
            *   `IMPORTA`: Abre un portal a otro archivo `.zk`, ejecutándolo en su propio pequeño universo.
        *   **Flujo de Control**: `SI`, `MIENTRAS`, `PARA`, `TRY_CATCH` se comportan como sus contrapartes en otros lenguajes, manejando excepciones como `BreakException` para alterar el flujo.
        *   **Expresiones**: Cálculos, llamadas a función (`mi_func()`), acceso a tesoros (`objeto.propiedad`, `lista[indice]`), creación de nuevas entidades (`nuevo MiClase()`).
        *   **Literales y Nombres**: Los valores directos y la resolución de identificadores a sus valores.
*   **`evaluate(self, code, ...)`**: El ritual completo: `Lexer -> Parser -> Optimizer (opc) -> Compiler (info) -> Execute`.
*   **`run_repl(self)`**: El bucle encantado que te permite hablar con Zisk.
*   **Comandos del Grimorio (`handle_repl_command`)**: Interpreta tus órdenes especiales (ej. `:cargar`).
</details>

---

## ⚙️ La Gran Sinfonía: Cómo el Código Zisk Cobra Vida

1.  🗣️ **Tú pronuncias el encantamiento** (escribes código Zisk).
2.  🪄 `ZiskREPL.run_repl()` lo escucha.
3.  ✨ Llama a `ZiskREPL.evaluate(codigo)`:
    a.  📜 `ZiskLexer` lo transcribe a tokens.
    b.  🗺️ `ZiskParser` dibuja el mapa (AST).
    c.  🔮 (Opcional) `ZiskOptimizer` lo refina.
    d.  🐍 (Informativo) `ZiskCompiler` lo traduce a Python.
    e.  🚀 `ZiskREPL.execute()` desata su poder, recorriendo el AST y haciendo que las cosas sucedan.
4.  💬 El REPL te muestra el resultado.
5.  🔁 El ciclo se reinicia, ¡esperando más magia!

---

## 🚀 Cómo Blandir Zisk: Primeros Pasos

### 1. Iniciar el REPL (La Esfera de Adivinación)

```bash
python tu_archivo_zisk_interprete.py
