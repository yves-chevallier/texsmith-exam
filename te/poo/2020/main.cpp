#include "simulator.hpp"

int main() {
    Monitor system1{1};
    Monitor system2{2};
    Sensor sensor1{10};
    Sensor sensor2{20};

    sensor1.connect(system1);
    sensor1.connect(system2);

    // Alert generated on s1 and s2
    sensor1.read(1600);
}
