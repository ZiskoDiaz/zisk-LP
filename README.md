# ⚜️ Zisk: Arquitectura de un Intérprete Dinámico y su REPL ⚜️

## 🔹 I. Visión General

Zisk se erige como un lenguaje de programación interpretado, cuyo ecosistema se materializa en este proyecto a través de un intérprete robusto y un REPL (Read-Eval-Print Loop) de alta interactividad. Desarrollado en Python 3, Zisk es una sinfonía de componentes meticulosamente diseñados que colaboran para analizar, optimizar opcionalmente, compilar tentativamente a Python, y ejecutar código Zisk con precisión.

> **El REPL de Zisk: Un Ciclo de Procesamiento Refinado**
>
> 1.  📥 **Recepción (Lee):** Captura el código Zisk introducido por el usuario, ya sea como directivas individuales o bloques estructurados.
> 2.  ⚙️ **Procesamiento (Evalúa):**
>     *   🔩 **`ZiskLexer` (Tokenizador):** Segmenta el código fuente en unidades léxicas fundamentales (tokens): directivas clave, identificadores, literales numéricos, operadores simbólicos.
>     *   🌲 **`ZiskParser` (Analizador Sintáctico):** Construye un Árbol de Sintaxis Abstracta (AST) a partir de la secuencia de tokens, representando la jerarquía estructural del código.
>     *   🔬 **`ZiskOptimizer` (Optimizador):** (Opcional) Aplica transformaciones estratégicas al AST para potenciar la eficiencia (ej. plegado de constantes).
>     *   🧠 **Motor de Ejecución (en `ZiskREPL.execute`):** El núcleo operativo que navega el AST, administrando variables, ámbitos, flujos de control y la semántica de las operaciones.
>     *   🛡️ **`ZiskTypeSystem` (Sistema de Tipos):** Supervisa la coherencia y compatibilidad de tipos durante la ejecución (y potencialmente en fases previas), facilitando la inferencia y validación.
> 3.  📤 **Resultado (Imprime):** Presenta la salida de la evaluación (si existe) en la consola.
> 4.  🔁 **Iteración (Bucle):** Reinicia el ciclo, preparado para la siguiente entrada.

Adicionalmente, el sistema incorpora un **`ZiskCompiler`**, con la capacidad de transcribir el AST de Zisk a código Python, abriendo la posibilidad de "compilar" scripts Zisk. El REPL está enriquecido con comandos de utilidad (ej. `:load`, `:help`) para una experiencia de desarrollo ágil.

---

## 🔹 II. Componentes Fundamentales del Sistema

<details>
<summary>❗ <strong>Gestión de Excepciones: Protocolos de Error</strong></summary>

Zisk implementa un sistema de excepciones personalizado para un diagnóstico de errores preciso y contextualizado.

*   **`ZiskError(Exception)`**: Clase base para todas las anomalías en Zisk. Encapsula mensaje, línea y columna.
    *   **`ZiskTypeError(ZiskError)`**: Para conflictos de signatura de tipos.
    *   **`ZiskRuntimeError(ZiskError)`**: Errores genéricos detectados durante la fase de ejecución.
    *   **`ZiskAttributeError(ZiskRuntimeError)`**: Para intentos de acceso a atributos/propiedades no definidos.
    *   **`ZiskIndexError(ZiskRuntimeError)`**: Para direccionamiento fuera de los límites de secuencias.
    *   **`ZiskKeyError(ZiskRuntimeError)`**: Para referencias a claves inexistentes en colecciones asociativas.
*   **`BreakException(Exception)`**: Mecanismo interno para la directiva `break`.
*   **`ContinueException(Exception)`**: Mecanismo interno para la directiva `continua`.
*   **`ReturnException(Exception)`**: Mecanismo interno para la directiva `retorna`, portando el valor de retorno.
</details>

<details>
<summary>🔩 <strong>`ZiskLexer`: El Ingeniero Léxico</strong></summary>

Responsable de la transformación del código fuente en una secuencia estructurada de tokens.

*   **`__init__(self)`**:
    *   Define `self.tokens_spec`: Un catálogo de especificaciones de tokens (nombre y patrón regex). Las palabras clave se priorizan por longitud para una correcta disambiguación.
    *   Precompila los patrones regex para optimizar el rendimiento del análisis.
*   **`tokenize(self, code: str) -> List[Tuple[str, str, int, int]]`**:
    *   Procesa el código de entrada, identificando tokens según las especificaciones.
    *   Descarta elementos no estructurales como comentarios y espacios en blanco.
    *   Caracteres no reconocibles (`NO_VALIDO`) generan un `ZiskError`.
    *   Produce una lista de tuplas: `(TIPO_TOKEN, VALOR_TOKEN, NUM_LINEA, NUM_COLUMNA)`.
</details>

<details>
<summary>🌲 <strong>`ZiskParser`: El Arquitecto Sintáctico</strong></summary>

Construye el Árbol de Sintaxis Abstracta (AST) a partir de la secuencia de tokens, reflejando la gramática del lenguaje.

*   **`__init__(self)`**:
    *   Gestiona la lista de tokens, el token actual, y una pila de contextos (`self.scopes`) para el análisis semántico preliminar.
    *   `self.current_class`: Indicador de contexto para el parsing de definiciones de clase.
*   **Gestión de Ámbitos (Parser)**: Funciones para administrar la visibilidad y declaración de identificadores.
*   **`parse(self, tokens)`**: Inicia el proceso de construcción del AST.
*   **Estructuras de Parsing**:
    *   Métodos dedicados para cada construcción del lenguaje: `parse_funcion()`, `parse_clase()`, `parse_declaracion_variable()`, etc.
    *   Implementa una **Jerarquía de Precedencia de Operadores** para el correcto análisis de expresiones complejas.
    *   `parse_expresion_primaria()`: Analiza los componentes más elementales: literales, identificadores, `(expresiones)`, `nuevo Clase()`, `este`, `ingresar()`, `[]` (listas), y `{}` (objetos).
*   **`consume(self, ...)`**: Valida y avanza al siguiente token.
*   **El AST**: Una representación arborescente del código mediante tuplas anidadas. Ej: `('PROGRAMA', [('DECLARACION_VAR', 'x', 'entero', ('NUMERO', 10))])`.
</details>

<details>
<summary>🛡️ <strong>`ZiskTypeSystem`: El Verificador de Tipos</strong></summary>

Asegura la integridad y coherencia de los tipos de datos dentro del ecosistema Zisk.

*   **`__init__(self)`**:
    *   `self.type_map`: Correlaciona los designadores de tipo de Zisk (ej. `texto`) con sus equivalentes en Python (ej. `str`).
    *   Mantiene registros de anotaciones de tipo, jerarquías de clases y signaturas de métodos.
*   **`check_type(...)`**: Valida la compatibilidad de un valor Python con un tipo Zisk especificado.
*   **`infer_type(...)`**: Intenta deducir el tipo Zisk de un valor Python.
*   **`validate_assignment(...)`**: Determina si un valor es asignable a un contexto tipado (variable, parámetro, retorno).
*   Funciones adicionales para el registro y consulta de metadatos de tipos para clases, métodos y variables.
</details>

<details>
<summary>🔬 <strong>`ZiskOptimizer`: El Estratega de Optimización</strong></summary>

Aplica transformaciones selectivas al AST para mejorar la eficiencia y concisión del código.

*   **`__init__(self)`**: Configura la activación de pases de optimización específicos.
*   **`optimize(self, ast_node)`**:
    *   Procesa el AST (generalmente en post-orden).
    *   **Plegado de Constantes**: Reemplaza expresiones aritméticas con literales constantes por su resultado precalculado.
    *   **Eliminación de Código Inalcanzable**: Suprime bloques condicionales (`si`, `mientras`) cuya condición es estáticamente evaluable a `falso`.
</details>

<details>
<summary>🔄 <strong>`ZiskCompiler`: El Transcriptor a Python</strong></summary>

Traduce el Árbol de Sintaxis Abstracta de Zisk a código fuente Python equivalente.

*   **`__init__(self)`**: Gestiona el estado de la compilación, como el nivel de indentación.
*   **`compile(self, ast_node)`**:
    *   Recibe un nodo AST y genera su representación en Python.
    *   Contiene lógica específica para cada tipo de nodo AST:
        *   `funcion` Zisk ➡️ `def` Python.
        *   `clase` Zisk ➡️ `class` Python (incluyendo `__init__` y herencia).
        *   Funciones nativas Zisk (`mostrar`) ➡️ Funciones Python (`print`).
        *   Operadores lógicos (`&&`, `||`) ➡️ `and`, `or`.
    *   Produce código Python indentado y sintácticamente correcto.
    ```python
    # Fragmento de salida del compilador
    class EjemploZisk:
        def __init__(self):
            self.valor_instancia = None # type: entero
        def metodo_ejemplo(self, arg_zisk): # type: texto
            # -> booleano
            if len(arg_zisk) > 0:
                return True
            return False
    ```
</details>

<details>
<summary>🕹️ <strong>`ZiskREPL`: El Núcleo Interactivo y Motor de Ejecución</strong></summary>

El `ZiskREPL` orquesta la interacción con el usuario y contiene la lógica para la ejecución directa del AST.

*   **`__init__(self, ...)`**:
    *   Instancia y coordina los componentes: `ZiskLexer`, `ZiskParser`, `ZiskOptimizer`, `ZiskCompiler`, `ZiskTypeSystem`.
    *   **Contexto de Ejecución (`Runtime Environment`)**:
        *   `self.scopes`: Pila de ámbitos para la resolución de nombres y almacenamiento de variables.
        *   `self.functions`: Registro de funciones, tanto nativas del lenguaje como definidas por el usuario.
        *   `self.classes`: Catálogo de clases Zisk (representadas como clases Python generadas dinámicamente).
        *   `self.modules`: Colección de módulos Zisk importados.
        *   `self.current_self`: Referencia a la instancia actual (`este`) en métodos de objeto.
*   **Funciones Nativas (`_native_...`)**: Implementaciones Python para las funcionalidades incorporadas de Zisk.
*   **Gestión de Variables (Runtime)**: Funciones para declarar, asignar y recuperar variables, aplicando validaciones de tipo y constancia.
*   **`execute(self, ast_node)`**: **El intérprete del AST**.
    *   Navega el AST recursivamente, ejecutando la semántica de cada nodo:
        *   **Declaraciones**:
            *   `FUNCION`: Genera un closure Python que encapsula el cuerpo de la función Zisk, gestionando ámbitos y retornos.
            *   `CLASE`: Construye dinámicamente una clase Python, traduciendo métodos Zisk y configurando atributos.
            *   `IMPORTA`: Carga y ejecuta módulos externos `.zk` en un contexto aislado.
        *   **Estructuras de Control**: `SI`, `MIENTRAS`, `PARA`, `TRY_CATCH` implementan la lógica de flujo, respondiendo a excepciones de control.
        *   **Expresiones**: Se evalúan operaciones, llamadas a función, accesos a miembros/índices y se resuelven literales e identificadores.
*   **`evaluate(self, code, ...)`**: Proceso completo: `Lexer -> Parser -> Optimizer (opc) -> Compiler (info) -> Execute`.
*   **`run_repl(self)`**: Inicia el bucle interactivo, gestionando entradas, comandos y errores.
*   **Comandos de Consola (`handle_repl_command`)**: Procesa directivas especiales del REPL.
</details>

---

## 🔹 III. Flujo de Procesamiento Estándar

1.  ⌨️ **Usuario:** Introduce código Zisk.
2.  `ZiskREPL.run_repl()`: Captura la entrada.
3.  `ZiskREPL.evaluate(codigo)`:
    a.  `ZiskLexer.tokenize()` ➡️ `tokens`.
    b.  `ZiskParser.parse()` ➡️ `ast_original`.
    c.  (Opcional) `ZiskOptimizer.optimize()` ➡️ `ast_optimizado`.
    d.  (Informativo) `ZiskCompiler.compile()` ➡️ `codigo_python_compilado`.
    e.  `ZiskREPL.execute(ast_optimizado)` ➡️ `resultado_ejecucion`.
        *   `execute` atraviesa el AST, interactuando con el entorno de ejecución (`scopes`, `functions`, `classes`, `ZiskTypeSystem`).
4.  `ZiskREPL.run_repl()`: Muestra `resultado_ejecucion`.
5.  El ciclo se repite.

---

## 🔹 IV. Guía de Inicio Rápido

### 1. Iniciar el Entorno Interactivo (REPL)

```bash
python nombre_del_archivo_interprete.py
