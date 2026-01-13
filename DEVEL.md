- Suppress colors in links 
- Les consignes ne sont pas miss en forme (gras de nom et prénom)
- Ajouter espace sur première page pour nom/prénom prendre exemple sur...
- Résoudre problème callout solution 
- Fin du travail écrit "Fin" avec une capitale
- Support pour les fill-in-the-blank
- Support for multiple answers
- Support for boxes
- Générer documentation du package
- Ajouter CI
- Publier sur PyPI

# Fill in the blank syntax

A duck is an [animal] that have [two] legs and a beak usually colored in [yellow].

The template will adjust width automatically based on the length of the content based on a factor availble in attribute (char-width-scale: 1 by default) you can use superfences to specify the width: [animal]{width=3cm}, or short notation [animal]{w=30} (default unit is mm). This is replaced with the template in latex in \fillin[texte][2cm]

# Multiple answers

We can leverage the fill in the blank syntax to ask several inputs. For example, give three fruit names:

1. [apple]{w=50}
2. [banana]{w=50}
3. [pear]{w=50}

# Drawbox

Draw a sheep in the box. Box parameter will draw a box or the solution. You can configure the box size either by giving the height: `box=5cm` or both width and height `box=50x40` this time in mm.

!!! solution { box=50x50 } 

    ![sheep]{sheep.drawio}

# Configuration
