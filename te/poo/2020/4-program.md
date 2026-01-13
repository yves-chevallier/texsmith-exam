/// latex
\clearpage
///

# Programmation

L'objectif est de simuler un dispositif de sécurité pour un parking composés de capteurs et d'organes de lecture de ces capteurs. Le patron de conception observateur sera utilisé.

Une classe `Sensor` représente un capteur de CO2. Chaque capteur donne une valeur du taux de CO2 en ppm (parts par million). La valeur du capteur est contenue dans un attribut mis à jour par la méthode `read`. Ces capteurs mesurent le taux de CO2 dans le parking souterrain.

La méthode `read` est appellée automatiquement par un ordonnanceur externe et prend en paramètre la nouvelle valeur du capteur. Cette méthode vérifie le taux de CO2 et s'il dépasse le seul limite de 1500 ppm, tous les systèmes de monitoring connectés à ce capteur de CO2 sont notifiés via la méthode `notify`.

Un système de monitoring `Monitor` peut se connecter à un capteur via la méthode `connect`. Chaque capteur conserve donc la liste de tous les `Monitor` connectés.

Un système de monitoring `Monitor`, dispose d'une méthode `alert` qui reçoit en paramètre une référence sur le capteur dont la limite de CO2 a été dépassée.

La méthode `alert` se charge d'affiche sur la sortie standard l'identifiant du capteur et son taux actuel de CO2.

Chaque capteur possède un identifiant unique (int) définit à la construction.

## Diagramme UML { points=5 }

Écrire le diagramme de classe UML de ce système.

!!! solution

    Se compose de deux classes. Un capteur est une collection de moniteurs. Les moniteurs ne sont pas détruits lors de la destruction d'un capteur. Il s'agit donc d'une aggrégation.

    ![Diagramme UML](uml.pdf){ width=50% }

## En-tête { points=5 }

Déclarer la description des classes `Sensor` et `Monitor` sans les implémenter.

!!! solution

    ```cpp
    --8<--- "simulator.hpp"
    ```

## Implémentation { points=5 }

Implémentez les méthodes suivantes :

- **connect**: un système de monitoring se connecte à un capteur,
- **read**: méthode de `Sensor` qui déclanche la notification aux clients si le taux de CO2 dépasse la valeur limite,
- **notify**: méthode appelée par `read` notifie tous les systèmes de monitoring en appelant leur méthode `alert`,
- **alert**: methode du système de monitoring qui affiche le message sur la sortie standard.

!!! solution

    ```cpp
    --8<--- "simulator.cpp"
    ```

## Main { points=5 }

Créer quelques capteurs et quelques systèmes de monitoring en montrant la manière dont ils peuvent être interconnectés.

!!! solution

    Voici un exemple de programme principal `main.cpp` :

    ```cpp
    --8<--- "main.cpp"
    ```

    La compilation du projet pourrait se faire avec :

    ```bash
    $ g++ -std=c++11 -Wall simulator.cpp -osimulator.o
    $ g++ -std=c++11 -Wall main.cpp -omain.o
    $ g++ -std=c++11 -Wall main.o simulator.o -osimulator
    ```

/// latex
\ifprintanswers
\else
\clearpage
\fillwithdottedlines{\stretch{1}}
\clearpage
\fillwithdottedlines{\stretch{1}}
\fi
///
