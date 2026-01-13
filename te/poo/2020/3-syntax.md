/// latex
\clearpage
///

# Syntaxe { points=10 }

Deux points par bonne réponse.

## -

Qu'écrire dans la fonction main pour appeler la fonction `burried` ?

```cpp
namespace qux {
    namespace foo {
        namespace bar {
            int burried() {
                return 42;
            }
        }
    }
}

using namespace qux;

int main() {
    ...
}
```

!!! solution { lines=2 }

    ```cpp
    return foo::bar::burried();
    ```

## -

Écrire la classe suivante ainsi que son implémentation: une classe `Square` représente un carré de côté `edge`. Ce côté est initialisé au constructeur. La somme de deux carrés est un carré dont la surface est la somme des surfaces de ces deux carrés. La méthode `area` retourne la surface d'un carré.

```cpp
Square a{10};
Square b{5};
Square c = a + b; // Permettre l'addition de deux carrés !
assert(c.area() == 125)
```

!!! solution { lines=12 }

    ```cpp
    struct Square {
        const int edge;
        Square(const int edge) : edge{edge} {}
        double area() const { return edge * edge; }
        Square& operator+(const Square &other) {
            return sqrt(
                this.area() + other.area());
        }
    };
    ```

---

## -

Une classe définissant un point dans un espace à deux dimensions peut être construit en donnant deux paramètres à son constructeur, la coordonnée `x`, puis la coordonnée `y`. Les coordonnées ne peuvent plus être changées une fois le point construit. La classe est générique et il doit être possible de créer un point sur n'importe quel type numérique (`int`, `double`...). Implémentez cette description.

!!! solution { lines=8 }

    ```cpp
    template <typename T>
    struct Point {
        const T x, y;
        Point(T x, T y) : x{x}, y{y} {}
    };
    ```

## -

Une fonction `divideOrFail` retourne la division de deux nombres flottants. Dans le cas ou le diviseur est nul, cette fonction lève une exception de type `std::runtime_error` qui hérite de `std::exception`. Une instance de ce type est constuite avec un paramètre : le message d'erreur. Écrire la fonction `divideOrFail`.

!!! solution { lines=8 }

    ```cpp
    double divideOrFail(double a, double b) {
        if (b == 0)
            throw std::runtime_error("Error");
        return a / b;
    }
    ```

## -

Déclarez un *smart pointer* qui ne peut contenir qu'une seule référence, avec une instance de `Foo`. Cette classe dispose d'un constructeur par défaut sans paramètres.

!!! solution { lines=3 }

    ```cpp
    std::unique_ptr<Foo> p = std::make_unique<Foo>();
    ```
