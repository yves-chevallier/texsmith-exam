#include "simulator.hpp"

#include <set>
#include <iostream>

using namespace std;

#define LIMIT 1500 /* ppm */

void Monitor::alert(Sensor &sensor) const {
    cout << "Monitor " << id << " : ";
    cout << "Alert from sensor " << sensor.id;
    cout << ", CO2 level " << sensor.getValue() << endl;
}

void Sensor::connect(Monitor &monitor) {
    clients.insert(monitor);
}

void Sensor::read(double value) {
    this->value = value;
    if (value > LIMIT) notify();
}

void Sensor::notify() {
    for (auto &client : clients)
        client.alert(*this);
}

double Sensor::getValue() { return value; }
