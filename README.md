<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Documentación Zisk</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-800 leading-relaxed">

  <main class="max-w-4xl mx-auto p-6">
    
    <header class="mb-8">
      <h1 class="text-4xl font-extrabold text-indigo-700 mb-2">📘 Documentación del Intérprete y REPL de Zisk</h1>
      <p class="text-lg text-gray-600">Una guía técnica del funcionamiento interno del lenguaje Zisk</p>
    </header>

    <section class="mb-12">
      <h2 class="text-2xl font-bold text-indigo-600 mb-4">1. Introducción</h2>
      <p class="mb-4">
        <strong>Zisk</strong> es un lenguaje de programación interpretado. Este proyecto implementa un intérprete completo junto con un REPL (<em>Read-Eval-Print Loop</em>) para interactuar con él. El sistema está construido en Python 3 y consta de varios componentes clave que trabajan juntos.
      </p>

      <div class="bg-white shadow p-4 rounded border-l-4 border-indigo-500 mb-6">
        <h3 class="font-semibold text-lg text-indigo-700 mb-2">¿Qué hace el REPL de Zisk?</h3>
        <ol class="list-decimal list-inside space-y-2 text-sm">
          <li><strong>Lee</strong> el código Zisk introducido por el usuario.</li>
          <li><strong>Evalúa</strong> el código mediante distintos componentes:
            <ul class="list-disc list-inside ml-4">
              <li><code>ZiskLexer</code>: tokeniza el código.</li>
              <li><code>ZiskParser</code>: construye el AST.</li>
              <li><code>ZiskOptimizer</code>: aplica optimizaciones simples.</li>
              <li><code>ZiskREPL.execute</code>: ejecuta instrucciones desde el AST.</li>
              <li><code>ZiskTypeSystem</code>: valida e infiere tipos.</li>
            </ul>
          </li>
          <li><strong>Imprime</strong> el resultado en la consola.</li>
          <li><strong>Repite</strong> el ciclo.</li>
        </ol>
      </div>

      <p class="mb-2">
        Además, el sistema cuenta con un <code class="bg-gray-200 rounded px-1">ZiskCompiler</code> que traduce código Zisk a Python ejecutable, y comandos especiales del REPL como <code class="bg-gray-200 rounded px-1">:cargar</code> o <code>:ayuda</code>.
      </p>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-bold text-indigo-600 mb-4">2. Componentes del Sistema</h2>

      <article class="mb-10">
        <h3 class="text-xl font-semibold text-indigo-500 mb-2">2.1 Excepciones Personalizadas</h3>
        <p class="mb-2">Zisk implementa su propia jerarquía de excepciones para un manejo de errores más claro:</p>
        <ul class="list-disc list-inside space-y-1">
          <li><code>ZiskError</code>: clase base.</li>
          <li><code>ZiskTypeError</code>, <code>ZiskRuntimeError</code>, <code>ZiskAttributeError</code>...</li>
          <li><code>BreakException</code>, <code>ContinueException</code>, <code>ReturnException</code>: control de flujo interno.</li>
        </ul>
      </article>

      <article class="mb-10">
        <h3 class="text-xl font-semibold text-indigo-500 mb-2">2.2 ZiskLexer (Analizador Léxico)</h3>
        <p>Convierte texto fuente a tokens. Maneja:</p>
        <ul class="list-disc list-inside space-y-1 ml-4">
          <li>Espacios y comentarios</li>
          <li>Errores de tokenización</li>
          <li>Posición (línea y columna)</li>
        </ul>
        <p class="text-sm mt-2 text-gray-600">Devuelve una lista de tuplas con tipo, valor y ubicación.</p>
      </article>

      <article class="mb-10">
        <h3 class="text-xl font-semibold text-indigo-500 mb-2">2.3 ZiskParser (Analizador Sintáctico)</h3>
        <p>Construye el AST y realiza análisis semántico ligero. Incluye:</p>
        <ul class="list-disc list-inside ml-4 space-y-1">
          <li>Parsing de funciones, clases, sentencias y expresiones</li>
          <li>Gestión de ámbitos y validación de declaraciones</li>
          <li>Jerarquía de expresiones con precedencia</li>
        </ul>
      </article>

      <article class="mb-10">
        <h3 class="text-xl font-semibold text-indigo-500 mb-2">2.4 ZiskTypeSystem (Sistema de Tipos)</h3>
        <p>Valida asignaciones, inferencias y herencias entre clases:</p>
        <ul class="list-disc list-inside ml-4 space-y-1">
          <li>Mapeo entre tipos Zisk y Python</li>
          <li>Firmas de métodos y clases</li>
          <li>Inferencia y verificación en llamadas y retornos</li>
        </ul>
      </article>

      <article class="mb-10">
        <h3 class="text-xl font-semibold text-indigo-500 mb-2">2.5 ZiskOptimizer (Optimizador)</h3>
        <p>Aplica transformaciones simples al AST como:</p>
        <ul class="list-disc list-inside ml-4 space-y-1">
          <li>Plegado de constantes</li>
          <li>Eliminación de código muerto (condicionales y bucles vacíos)</li>
        </ul>
      </article>

      <article class="mb-10">
        <h3 class="text-xl font-semibold text-indigo-500 mb-2">2.6 ZiskCompiler (Compilador a Python)</h3>
        <p>Convierte AST de Zisk a código Python ejecutable. Implementa:</p>
        <ul class="list-disc list-inside ml-4 space-y-1">
          <li>Control de indentación</li>
          <li>Evita duplicar imports</li>
          <li>Traducción nodo por nodo</li>
        </ul>
      </article>
    </section>

  </main>
</body>
</html>
