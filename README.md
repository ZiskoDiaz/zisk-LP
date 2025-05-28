# 🧠 Manual Básico del Lenguaje Zisk `.zk`

Bienvenido al lenguaje **Zisk**, un lenguaje simple, intuitivo y expresivo para aprender lógica de programación con sintaxis amigable. Este manual cubre:

- Variables y constantes
- Operaciones básicas
- Comparaciones
- Operadores lógicos
- Control de flujo (condicionales y bucles)
- Funciones
- Entrada de usuario

> 📁 Todos los archivos deben tener extensión `.zk`

---

## 📦 1. Variables y Constantes

```zisk
var numero = 10;
const PI = 3.14;
var saludar = "Hola Mundo";
var miLista = [1, 2, 3, 4, 5];
var miObjeto = {"nombre": "Juan", "edad": 30};

mostrar(numero);
mostrar(PI);
mostrar(saludar);
mostrar(miLista);
mostrar(miObjeto);
```

🔍 **¿Qué hace este código?**

- `var`: declara una variable (puede cambiar).
- `const`: declara una constante (no se puede modificar).
- Las variables pueden ser números, texto, listas, o incluso objetos.
- `mostrar(...)`: imprime en pantalla lo que se pasa como parámetro.

---

## ➕ 2. Operatoria Básica

```zisk
var suma = 5 + 3;
var resta = 10 - 4;
var multiplicacion = 6 * 7;
var division = 20 / 4;
var modulo = 10 % 3;

mostrar("el resultado de la suma es", suma);
mostrar("el resultado de la resta es", resta);
mostrar("la multiplicaciones ", multiplicacion);
mostrar("el resultado de la division es ", division);
mostrar("el resto de 10 entre 3 es ", modulo);
```

📌 **Explicación:**

| Operador | Significado         |
|----------|---------------------|
| `+`      | Suma                |
| `-`      | Resta               |
| `*`      | Multiplicación      |
| `/`      | División            |
| `%`      | Módulo (resto)      |

---

## ⚖️ 3. Comparaciones

```zisk
var igual = 5 == 5;
var diferente = 5 != 3;
var mayor = 10 > 5;
var menor = 3 < 7;
var mayorIgual = 10 >= 10;
var menorIgual = 5 <= 10;

mostrar("¿5 == 5? ", igual);
mostrar("¿5 es distinto de 3? ", diferente);
mostrar("¿10 > 5? ", mayor);
mostrar("¿3 < 7? ", menor);
mostrar(mayorIgual, menorIgual);
```

📌 **Explicación:**

| Operador | Significado                      |
|----------|----------------------------------|
| `==`     | Igual a                          |
| `!=`     | Distinto de                      |
| `>`      | Mayor que                        |
| `<`      | Menor que                        |
| `>=`     | Mayor o igual que                |
| `<=`     | Menor o igual que                |

---

## 🔗 4. Operadores Lógicos

```zisk
var and = verdadero && verdadero;
var or = verdadero || falso;
var not = !falso;

mostrar(and, or, not);
```

🧠 **Lógica booleana:**

| Operador | Significado       | Ejemplo                | Resultado |
|----------|-------------------|------------------------|-----------|
| `&&`     | Y lógico (AND)    | verdadero && falso     | falso     |
| `||`     | O lógico (OR)     | verdadero || falso     | verdadero |
| `!`      | Negación (NOT)    | !falso                 | verdadero |

---

## 🔁 5. Control de Flujo (Condicionales)

```zisk
var numeroSi = 10;

si (numeroSi > 5) entonces {
    mostrar("El numero es mayor que 5");
} sino {
    mostrar("El numero es menor o igual a 5");
}
```

🧩 **Explicación:**

- `si (...) entonces {...}`: ejecuta el bloque si la condición es verdadera.
- `sino {...}`: ejecuta si la condición es falsa.

---

## 🔂 6. Bucles

### ⏳ Mientras (while)

```zisk
var valorBase = 0;

mientras (valorBase < 5) {
    mostrar("Contador:", valorBase);
    valorBase = valorBase + 1;
}
```

📌 Ejecuta el bloque mientras `valorBase < 5`.

---

### 🔃 Para (for)

```zisk
para (var i = 0; i < 3; i = i+1) {
    mostrar("Iteracion:", i);
}
```

📌 Bucle clásico de contador: empieza en 0, incrementa hasta 2.

---

### 🧪 Hacer mientras (experimental)

```zisk
# var j = 0;
# hacer_mientras {
#    mostrar("Hacer mientras:", j);
#    j = j + 1;
# } (j < 3);
```

🧠 *Este bloque está comentado, pero sugiere que Zisk incluirá un `do-while`.*

---

## 🧠 7. Funciones

```zisk
funcion suma(a , b) {
    retorna a + b;
}

funcion resta(a, b) {
    retorna a - b;
}

funcion multiplicar(a, b) {
    retorna a * b;
}

funcion dividir(a, b) {
    si (b == 0) {
        mostrar("Error: Division por cero");
        retorna 0;
    }
    retorna a / b;
}

var a = 5;
var b = 10;

mostrar("Suma:", suma(a,b)); 
mostrar("Resta:", resta(a,b));
mostrar("Multiplicacion:", multiplicar(a,b));
mostrar("Division:", dividir(a,b));
```

📌 **Explicación:**

- `funcion nombre(params) { ... }`: define una función.
- `retorna`: devuelve un valor al que llamó la función.

---

## ⌨️ 8. Entrada de Usuario

```zisk
mostrar("Hola,", ingresar("Ingresa tu nombre: "));
```

🧑‍💻 **¿Qué hace?**

- `ingresar(...)`: muestra un prompt y espera un valor.
- `mostrar(...)`: imprime el resultado concatenado con texto.

---

## 🗂️ Archivos y Convenciones

- Todos los archivos de código deben guardarse con extensión `.zk`.
- Usa nombres descriptivos: `calculadora.zk`, `usuario.zk`, `bucles.zk`.

---


## 📢 Créditos

> Manual creado por **Francisco Díaz** – Desarrollador de Zisk  
> Versión: `v0.1.0` – En constante evolución 🚀  
> ¡Hackea, prueba y comparte!
