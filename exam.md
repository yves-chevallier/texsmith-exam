---
author: Prof. Yves Chevallier
date: 2026-05-01
exam:
  type: TE
  department: TIN
  school: HEIG-VD
  course: Info1
  rules:
    - Écrire votre **nom** et votre **prénom** lisiblement sur chaque page.
    - Écrire lisiblement, au stylo ou au crayon à papier gras.
    - Répondre aux questions dans les zones appropriées.
    - Relire toutes vos réponses avant de rendre votre travail.
    - Vérifier que vous n'avez pas oublié de compléter une page de l'examen.
    - Rendre toutes les feuilles, une feuille par problème.
    - Rendre toutes les feuilles de brouillon ainsi que la page de couverture.
    - Les réponses données sur les feuilles de brouillon ne sont ni acceptées ni corrigées.
    - Aucun moyen de communication autorisé.
    - Toutes les réponses concernent le langage C et son standard C17.

---
# Examen final

## Expressions { points=10 }

Considérez les déclarations suivantes :

```c
#include <math.h>
#include <limits.h>
#define M 64
double x, y, z;
int i, j, k; // 32 bits
unsigned char c;
```

Supposez que toutes les variables ont été initialisées avec certaines valeurs valides puis pour chacun des énoncés suivants, construire une expression C valide adaptée. Aucun mot-clef de structure de contrôle n'est autorisé.

L'exemple ci-après donne une expression pour le discriminant d'une équation du second degré donnant 1 si le discriminant est positif ou nul, 0 sinon.

```c
(y*y - 4*x*z) >= 0 && x != 0
```

### _

L'expression retourne la moyenne géométrique de `x`, `y` et `z` exprimée comme $\sqrt[3]{x \cdot y \cdot z}$. Notez que la racine cubique est équivalente à la puissance $\frac{1}{3}$.

!!! solution { lines=1 }

    ```c
    pow(x * y * z, 1.0/3.0)
    ```

### _

L'expression retourne la partie entière (arrondie à la valeur inférieure) du logarithme base 2 de la variable `i` ; on suppose $i > 0$.

!!! solution { lines=1 }

    ```c
    floor(log10(i)/log10(2))
    ```

### _

L'expression est vraie ^^si et seulement si^^ la somme de `x`, `y` et `z` est comprise strictement entre $10$ et $20$.

!!! solution { lines=1 }

    ```c
    (x + y + z) > 10 && (x + y + z) < 20
    ```

### _

L'expression retourne la taille, en ^^bits^^, du type `int` tel que défini sur le système.

!!! solution { lines=1 }

    ```c
    sizeof(int) * CHAR_BIT
    ```

### _

L'expression est vraie si `i` et `j` sont impaires et que `k` est un multiple de `j`.

!!! solution { lines=1 }

    ```c
    i % 2 != 0 && j % 2 != 0 && k % j == 0
    ```

### _

L'expression retourne la somme de `i` et `j`, mais après son évaluation, `i` et `j` ont toutes les deux été décrémentées de $1$. N'utilisez que les opérateurs `--` et `+`.

!!! solution { lines=1 }

    ```c
    i-- + j--
    ```

### _

L'expression calcule la partie fractionnaire de $\frac{x}{y}$ ; on suppose que $y \neq 0$.

!!! solution { lines=1 }

    ```c
    x / y - (int)(x / y)
    ```

### _

L'expression est vraie ^^si et seulement si^^ le code ASCII contenu dans `c` correspond à un caractère dans les intervalles allant de `'0'` à `'9'` ou de `'a'` à `'f'`, toutes bornes incluses.

!!! solution { lines=1 }

    ```c
    (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')
    ```

### _

L'expression retourne la valeur des 4 bits de poids fort de l'inverse (bit à bit) de la variable `c` ; la valeur doit être ramenée à l'intervalle compris entre 0 et 15 inclus.

!!! solution { lines=1 }

    ```c
    (~c >> 4) & 0xF
    ```

### _

L'expression est vraie si les variables `x`, `x` et `y` sont strictement dans un ordre décroissant soit $x > y > z$.

!!! solution { lines=1 }

    ```c
    x > y && y > z
    ```

## Choix multiples { points=2 }

Pour chaque question, une seule des quatre réponses proposées est correcte. Indiquez la lettre correspondant à la bonne réponse.

### _

Quel est le résultat de l'expression C suivante si `i` vaut `5` et `j` vaut `2` ?

```c
i / j * 2 + i % j
```

- [x] 6
- [ ] 7
- [ ] 8
- [ ] 9

### _

Combien de pattes a un mille-pattes ?

- [ ] 1000
- [ ] 5000
- [x] Ça dépend des espèces
