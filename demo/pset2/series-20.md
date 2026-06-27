---
title: Série 0x20
subtitle: Révision du cours Info1
tags:
- arithmetic-expressions
- type-conversion
- control-structures
- debugging
exam:
  course: INFO2-TIN

---
# Algorithmique { points=6 }

## - { points=2 }

On souhaite développer un programme qui analyse un fichier de mesures passé sur l'entrée standard. Proposez une décomposition en sous-problèmes (raffinage successif) en listant 4 à 6 fonctions possibles, avec un nom clair pour chaque fonction.

!!! solution { lines=6 }

    Voici une proposition de décomposition en fonctions pour le programme d'analyse de mesures :

    1. `read_input` : lire l'entrée standard et stocker les données dans une structure appropriée
    2. `parse_measurement` : parser une ligne en structure de mesure
    3. `compute_stats` : calculer min, max, moyenne
    4. `print_report` : afficher le rapport
    5. `save_csv` : exporter les résultats

## - { points=2 }

Pour chaque tâche ci-dessous, indiquez si elle doit être réalisée dans une fonction distincte ou peut rester dans `main`, et justifiez en une phrase.

1. Lecture d'un argument de ligne de commande
2. Validation du format d'une date ISO8601
3. Calcul d'une distance euclidienne
4. Écriture d'un rapport dans un fichier

!!! solution { lines=6 }

    1. Peut rester dans `main` (simple, spécifique au programme).
    2. Fonction distincte (réutilisable et testable).
    3. Fonction distincte (réutilisable, calcul pur).
    4. Fonction distincte (sépare I/O et logique).

## - { points=2 }

Complétez le pseudo-code en détaillant le raffinage successif (2 niveaux) pour l'algorithme suivant : "compter le nombre de valeurs positives dans un tableau".

!!! solution { lines=6 }

    Niveau 1 :

    - parcourir le tableau
    - compter les valeurs positives
    - retourner le compteur

    Niveau 2 (détail du parcours) :

    - initialiser `count` à 0
    - pour chaque élément `x`, si `x > 0` alors `count++`

# Arithmétique et expressions { points=10 }

Considérez les déclarations suivantes :

```c
char c = 3;    short s = 7;
int i = 3;     long l = 4;
float f = 3.3; double d = 7.7;
```

Pour chacune des expressions ci-dessous, indiquez leur type et leur valeur. Par exemple l'expression `2 / 3 * c` donne `(int)0` car `2 / 3` est égal à `0` en division entière, et comme l'opération passe par l'ALU, le resultat est promu en `int` avant d'être multiplié par `c`.

## - { points=2 answer="`(int)1`" }

`c / 2`

## - { points=2 answer="`(int)7`" }

`s + c / 10`

## - { points=2 answer="`(double)5.5`" }

`l + i / 2.0`

## - { points=2 answer="`(double)11`" }

`d + f`

## - { points=2 answer="`(float)10.3`" }

`(int)d + f`

## - { points=2 answer="`(long)11`" }

`(int)d + l`

## - { points=2 answer="`(int)12`" }

`c << 2`

## - { points=2 answer="`(int)0`" }

`s & 0xf0`

## - { points=2 answer="`(int)1`" }

`s && 0xf0`

## - { points=2 answer="`(int)0`" }

`d + f == s + l`

# Analyse de code

Dans chacune des structures de contrôle ci-dessous, indiquer la nature de l'erreur.

## - { points=2 }

```c
double x = 100.0;
size_t i = 0;
do
    x = x / 2.0;
    i++;
while (x > 1.0);
```

!!! solution { lines=2 }

    Il manque les accolades autour du bloc `do..while`.

---

## - { points=2 }

```c
long x = 100;
if (x = 0)
    printf("Erreur : la valeur 0 est interdite !\n");
```

!!! solution { lines=2 }

    Le test d'égalité utilise l'opérateur `==`. L'opérateur d'affectation `=` n'est pas valable.

## - { points=2 }

```c
double x = 100.0;
switch (x) {
    case 0:
        printf("x est nul.\n");
        break;
    default:
        print("OK.\n");
}
```

!!! solution { lines=2 }

    L'instruction `switch` n'est pas applicable à un type à virgule flottante.

## - { points=2 }

```c
for (int i = 0; i < 10; i++);
{
    printf("%d\n", i);
}
```

!!! solution { lines=2 }

    Le point virgule à la fin de l'instruction termine cette dernière. Le bloc formé des accolades n'appartient pas à la boucle.

## - { points=2 }

```c
int i = 0;
while i < 100
{
    printf("%d\n", ++i);
}
```

!!! solution { lines=2 }

    Il manque des parenthèses autour de la condition de l'instruction `while`.

---

## - { points=2 }

On s'intéresse ici au passage par adresse. Observez le programme suivant et indiquez ce que vous voyez sur la sortie standard.

```c
#include <stdio.h>
#include <stdlib.h>

int test(int a, int *b, int *c, int *d) {
    a = *b;
    *b = *b + 5;
    *c = a + 2;
    d = c;
    return *d;
}

int main() {
  int a = 0, b = 100, c = 200, d = 300, e = 400;
  e = test(a, &b, &c, &d);
  printf("%05d %d %d %d %d", a, b, c, d, e);
}
```

!!! solution { lines=1 }

    00000 105 102 300 102

# Programmation

## - { points=5 }

Algorithme sur les tableaux : écrire une fonction qui reçoit en paramètre un tableau d'entiers et qui retourne la position de la première occurrence d'une valeur dans ce tableau, ou `-1` si la valeur n'est pas présente. Utiliser la syntaxe pointeur pour le paramètre tableau.

!!! solution { lines=5 }

    ```c
    int index(int *array, size_t size, int value) {
      for (int i = 0; i < size; i++)
          if (array[i] == value)
              return i;
      return -1;
    }
    ```

## - { points=5 }

Écrire une fonction qui calcul la longueur totale des segments de droite dont les points sont reçus en paramètre. Les données sont un tableau composé de N par 2. Les indices du sous tableau sont les coordonnées X et Y des points.

!!! solution { lines=9 }

    ```c
    double distance(double x1, double y1, double x2, double y2) {
      return sqrt(pow(x2 - x1, 2) + pow(y2 - y1, 2));
    }

    double length(double array[][2], size_t size) {
      double length = 0;
      for (int i = 0; i < size - 1; i++)
          length += distance(
              array[i][0], array[i][1],
              array[i + 1][0], array[i + 1][1]
          );
      return length;
    }
    ```
