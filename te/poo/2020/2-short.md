## Réponses courtes { points=10 }

### -

Quelle est la sortie (stdout) de ce programme ?

```cpp
#include <iostream>

struct A {
    A() { std::cout << 8; }
    ~A() { std::cout << 4; }
};

int main(int argc, const char * argv[]) {
    if (argc > 0) {
        volatile A a;
        std::cout << 3;
    }
}
```

!!! solution { lines=1 }

    ```plaintext
    834
    ```

### -

Quelle est la sortie (stdout) de ce programme ?

```cpp
struct Foo { };

int main() {
    std::unique_ptr<Foo> a{nullptr};
    std::unique_ptr<Foo> b = std::make_unique<Foo>();
    a = std::move(b);
    std::cout << (a == nullptr) << (b == nullptr);
}
```

!!! solution { lines=1 }

    ```plaintext
    01
    ```

### -

Un réseau d'alerte est composés de participants. Chaque participant dispose d'un remplacant également membre du réseau d'alerte. En cas d'alerte on essaye de contacter chaque participant en partant du premier. En cas d'échec de contact, on passe à son remplacant. À tout moment, un participant peut décider de se retirer temporairement du réseau d'alerte. Quelle structure de donnée de la STL allez-vous préférablement utiliser pour gérer ce réseau d'alerte ?

!!! solution { lines=2 }

    ```plaintext
    Une liste chaînée (`std::list`) permet d'insérer et de supprimer des participants efficacement. La `forward_list` peut aussi être utilisée si on n'a pas besoin de parcourir la liste en arrière.
    ```

### -

Quelle est la sortie (stdout) de ce programme ?

```cpp
#include <iostream>
using namespace std;

struct A {
    A() { cout << 0; }
    virtual void foo() const { cout << 1; }
    void bar() const { cout << 2; }
    virtual ~A() { cout << 3; }
};

struct B : public A {
    B() { cout << 4; }
    void foo() const override { cout << 5; }
    void bar() const { cout << 7; }
    virtual ~B() override { cout << 6; }
};

int main() {
    A *ptr = new B;
    ptr->foo();
    ptr->bar();
    delete ptr;
}
```

!!! solution { lines=1 }

    ```plaintext
    045263
    ```

### -

L'utilisation de méthodes virtuelles a un impact sur les performances d'exécution d'un programme embarqué. Pouvez-vous expliquer pourquoi ?

!!! solution { lines=5 }

    Les méthodes virtuelles sont implémentées via une table de pointeurs de fonctions (vtable). L'appel d'une méthode virtuelle nécessite une indirection supplémentaire pour accéder à cette table, ce qui ajoute une surcharge en temps d'exécution par rapport à un appel de méthode non virtuelle direct.

### -

Pouvez-vous citer trois types différents de diagrammes décrits par le standard UML ?

!!! solution { lines=3 }

    Diagrammes de classe, d'activités, de composants, de paquets, de cas d'utilisations, d'états...

### -

Dans un diagramme de classe UML, pouvez-vous visuellement montrer trois types de relations différentes entre classes et expliquer la nature de ces relations ?

!!! solution { lines=3 }

    Notons les relations : composition, aggrégation et héritage sur la figure suivante.

    ![Relations UML](uml.pdf){ width=50% }

    - **A** est composé d'éléments **B**. Lorsque **A** est détruit, les éléments **B** le sont aussi.
    - **A** est associé aux éléments **D**. Lorsque **A** est détruit, les éléments **D** subsistent.
    - **C** hérite de **A**.

### -

Pouvez-vous citer 2 noms de *design pattern* utilisés en programmation orientée objets ?

!!! solution { lines=2 }

    Singleton, Factory, Observer, Strategy, Decorator, Adapter, Composite, Proxy...

### -

Pouvez vous expliquer brièvement la différence entre un objet et un attribut ?

!!! solution { lines=3 }

    Un objet est une instance d'une classe qui encapsule des données et des comportements. Un attribut est une variable membre d'une classe qui stocke des données spécifiques à l'objet.
