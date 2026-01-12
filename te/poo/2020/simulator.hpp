#pragma once
#include <set>

class Sensor;

struct Monitor {
    const int id;
    Monitor(int id) : id{id} {}
    void alert(Sensor &sensor) const;
    auto operator<=>(const Monitor &other) const {
      return id <=> other.id;
    }
};

class Sensor {
    double value;
    std::set<Monitor> clients;

  public:
    const int id;
    Sensor(int id) : id{id} {}
    void connect(Monitor &monitor);
    void disconnect(Monitor &monitor);
    void read(double value);
    void notify();
    double getValue();
};