# 🧠 Documentación del Intérprete y REPL de **Zisk**

---

## 📌 1. Introducción

**Zisk** es un lenguaje de programación interpretado. Este proyecto implementa:

- Un **intérprete completo**
- Un entorno interactivo tipo **REPL** (Read-Eval-Print Loop)

Construido en **Python 3**, el sistema permite:

> 🔁 Leer → Evaluar → (Opcional: Optimizar / Compilar) → Ejecutar

---

### 🔍 ¿Qué hace el REPL de Zisk?

1. **Lee** el código línea por línea o en bloques.
2. **Analiza y evalúa** el código:
   - 🧱 **`ZiskLexer`** → Tokeniza el texto.
   - 🌲 **`ZiskParser`** → Crea el AST (Árbol de Sintaxis Abstracta).
   - 🔧 **`ZiskOptimizer`** → (Opcional) Optimiza el AST.
   - ⚙️ **Motor de ejecución** → Interpreta y ejecuta el AST.
   - 🧬 **`ZiskTypeSystem`** → Verifica tipos en tiempo de ejecución.
3. **Imprime** los resultados.
4. **Repite** el ciclo.

> 💡 También permite **compilar a Python** usando `ZiskCompiler` y soporta comandos como `:cargar`, `:ayuda`.

---

## 🧩 2. Componentes del Sistema

### 🛑 2.1. Excepciones Personalizadas

| Clase | Descripción |
|-------|-------------|
| `ZiskError` | Base para errores del lenguaje. Incluye línea y columna. |
| └── `ZiskTypeError` | Tipos incompatibles |
| └── `ZiskRuntimeError` | Errores en tiempo de ejecución |
| └── `ZiskAttributeError` | Atributos inexistentes |
| └── `ZiskIndexError` | Índices fuera de rango |
| └── `ZiskKeyError` | Claves no encontradas |
| `BreakException`, `ContinueException`, `ReturnException` | Control de flujo interno |

---

### 🧾 2.2. `ZiskLexer` – Analizador Léxico

Convierte el código en **tokens**.

```python
token: (TIPO, VALOR, LINEA, COLUMNA)
