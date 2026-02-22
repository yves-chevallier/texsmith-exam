## Short Answers { points=10 }

### -

What is the output (stdout) of this program ?

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

!!! solution { lines=2 }

    The constructor of `A` is called when `a` is created, printing `8`. Then `3` is printed. When `a` goes out of scope at the end of the `if` block, the destructor of `A` is called, printing `4`. Thus, the output is:

    ```plaintext
    834
    ```

### -

Can you name the three primary colors in the RGB color model?

1. [red]{w=50}
2. [green]{w=50}
3. [blue]{w=50}

!!! solution

    The three primary colors in the RGB color model are defined from human vision which is trichromatic. Technology used in screens and digital imaging is based on this model.

### -

Can you name the three relations in the following diagram?

![Relations](assets/relationship.drawio){ width=50% }

#### -

[Composition]{w=100}

#### -

[Aggregation]{w=100}

#### -

[Inheritance]{w=100}
