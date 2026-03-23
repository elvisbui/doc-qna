# Classes in Python

## Defining a Class

Classes are defined using the `class` keyword. The `__init__` method is the constructor, called when a new instance is created.

```python
class Dog:
    def __init__(self, name, breed):
        self.name = name
        self.breed = breed

    def bark(self):
        return f"{self.name} says woof!"
```

## Instantiation

Create an instance by calling the class like a function:

```python
my_dog = Dog("Rex", "Labrador")
print(my_dog.bark())  # "Rex says woof!"
```

## Inheritance

A class can inherit from another class, gaining its attributes and methods:

```python
class ServiceDog(Dog):
    def __init__(self, name, breed, task):
        super().__init__(name, breed)
        self.task = task

    def describe(self):
        return f"{self.name} is a {self.breed} trained for {self.task}"
```

## Special Methods

Python classes can define special (dunder) methods to customize behavior:

- `__str__`: String representation for `print()` and `str()`.
- `__repr__`: Developer-friendly string representation.
- `__len__`: Called by `len()`.
- `__eq__`: Defines equality comparison with `==`.
- `__iter__` and `__next__`: Make objects iterable.

## Class vs Instance Attributes

- **Instance attributes** are defined in `__init__` using `self` and are unique to each instance.
- **Class attributes** are defined directly in the class body and shared among all instances.

```python
class Counter:
    count = 0  # class attribute

    def __init__(self):
        Counter.count += 1
```
