# Choix multiples { points=10 }

## -

Quelle bibliothèque C++ est utilisée pour lire et écrire sur l'entrée standard ?

- [x] `iostream`
- [ ] `stdio.h`
- [ ] `cstdio`
- [ ] `flow`
- [ ] `input-output`

## -

Quelle est la différence entre une classe et une structure en C++ ?

 - [ ] Aucune, les deux termes sont équivalents.
 - [ ] Une classe est publique par défaut alors qu'une structure est privée par défaut.
 - [x] Une classe est privée par défaut alors qu'une structure est publique par défaut.
 - [ ] Une structure ne possède pas de constructeur par défaut.

## -

Quels sont les éléments (plusieurs possibilités) que possèdent une classe ?

- [x] Un constructeur par défaut.
- [x] Un constructeur par copie.
- [x] Un opérateur d'affectation.
- [ ] Un attribut nommé `id`.
- [ ] Un destructeur privé.
- [x] Un destructeur public.
- [ ] Une méthode virtuelle.

## -

Que signifie l'esperluette dans l'exemple suivant ?

```cpp
class Foo {
    Bar &bar;
    Foo(Bar &bar) : bar{bar} {};
};
```

- [ ] `Bar` est un pointeur et `&` signifie l'adresse de.
- [x] La classe `Foo` possède une référence sur un objet `bar` déjà existant en dehors de l'instance.
- [ ] `bar` est constuit automatiquement à la compilation.
- [ ] `bar` existe obligatoirement dans le heap.
- [ ] Le signe signifie que l'objet `bar` devra être détruit par la classe `Foo` (RAII).

---

## -

Quel lien y-a-t-il entre la classe `Foo` et la classe `Bar` ?

```cpp
class Foo { };
class Bar : public Foo { };
```

- [ ] `Foo` hérite de `Bar`
- [x] `Bar` est un `Foo`
- [ ] `Bar` et `Foo` sont fusionnés en `Foobar`
- [ ] `Foo` est un `Bar`
- [ ] `Bar` est associé à `Foo`
- [ ] `Foo` est ami de `Bar`

## -

Considérant le code suivant, laquelle des propositions suivantes est la plus appropriée ?

```cpp
template<typename T, int S>
class Foo {
    size_t k;
    T data[S];
    public:
    Foo() : k{0} {}
    T add(T v) { return data[k++] = v; }
};
```

- [ ] Il s'agit d'un exemple de polymorphisme déterminé à l'exécution.
- [x] Il s'agit d'un exemple de polymorphisme déterminé à la compilation.
- [ ] Le type T représente un pointeur mémoire.
- [ ] Le tableau `T data[S]` est un élément de la STL.

## -

Laquelle des propositions suivantes est fausse concernant la structure de données associative `unordered_map` ?

- [ ] Permet la recherche rapide d'un élément en `O(1)`.
- [ ] S'appuie sur une fonction de hachage pour calculer la signature d'un objet.
- [x] Permet le tri rapide des éléments en `O(log·n)`.
- [ ] Permet l'ajout rapide d'un élément en `O(1)`.
- [ ] Ne conserve pas l'ordre dans lequel les éléments ont été insérés.

## -

En C++, lors de la copie d'une instance dans une classe `Foo` qui comporte la ligne suivante :

```cpp
Foo(const Foo &foo) = default;
```

- [ ] La copie est interdite.
- [x] La copie n'est possible qu'en surface.
- [ ] Il s'agit du concept de copie profonde.
- [ ] L'allocation dynamique n'est pas possible.

## -

Qu'est-ce qu'une classe d'interface ?

- [ ] Une classe portant un nom générique.
- [ ] Une classe virtuelle.
- [x] Une classe dont toutes les méthodes sont virtuelles pures.
- [ ] Une classe comportant `=default` sur toutes les méthodes.
- [ ] Une classe qui ne peut pas être dérivée.

## -

Qu'est-ce qu'un Singleton

- [ ] Une opération s'exécutant qu'une seule fois.
- [ ] Une instance de classe utilisable uniquement dans la fonction main.
- [x] Une classe ne pouvant posséder qu'une seule instance.
- [ ] Un type de polymorphisme dynamique.
- [ ] Une structure de donnée de taille unitaire.

---
