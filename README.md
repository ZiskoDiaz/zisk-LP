# Variables y constantes

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


---
**Archivo: `operatoria-basica.zk.md`**
```markdown
# Operatoria Basica

```zisk
var suma = 5 + 3;
var resta = 10 - 4;
var multiplicacion = 6 * 7;
var division = 20 / 4;
var modulo = 10 % 3;

mostrar("el resultado de la suma es", suma);
mostrar("el resultado de la resta es", resta);
mostrar("la multiplicaciones ",multiplicacion);
mostrar("el resultado de la division es ", division);
mostrar("el resto de 10 entre 3 es ",modulo);


---
**Archivo: `operadores-logicos.zk.md`**
```markdown
# Operadores lógicos

```zisk
var and = verdadero && verdadero;
var or = verdadero || falso;
var not = !falso;

mostrar(and, or, not);


---
**Archivo: `estructuras-de-control.zk.md`**
```markdown
# Estructuras de control

```zisk
var numeroSi = 10;

si (numeroSi > 5) entonces {
    mostrar("El numero es mayor que 5");
} sino {
    mostrar("El numero es menor o igual a 5");
}


---
**Archivo: `estructuras-de-control-bucles.zk.md`**
```markdown
# Estructuras de control bucles

```zisk
var valorBase = 0;
mientras (valorBase < 5) {
    mostrar("Contador:", valorBase);
    valorBase = valorBase + 1;
}


para (var i = 0; i < 3; i = i+1) {
    mostrar("Iteracion:", i);
}

# var j = 0;
# hacer_mientras {
#    mostrar("Hacer mientras:", j);
#    j = j + 1;
# } (j < 3);


---
**Archivo: `funciones.zk.md`**
```markdown
# Funciones

```zisk
var a = 5;
var b = 10;

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

mostrar("Suma:", suma(a,b));
mostrar("Resta:", resta(a,b));
mostrar("Multiplicacion:", multiplicar(a,b));
mostrar("Division:", dividir(a,b));


---
**Archivo: `entrada-de-usuario.zk.md`**
```markdown
# Entrada de usuario

```zisk
mostrar("Hola,", ingresar("Ingresa tu nombre: "));


---

Cada bloque de código está etiquetado con `zisk` para el resaltado de sintaxis en visores de Markdown que lo soporten (asumiendo que `zisk` sea un identificador reconocido o que se pueda configurar). Si no, se mostrará como un bloque de código genérico.
