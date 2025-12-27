class User:
    count = 0

    def __init__(self, name):
        self.name = name
        User.count += 1

    @classmethod
    def total_users(cls):
        return cls.count

print(User.total_users())    

class MathUtil:
    base = 10
    def __init__(self) -> None:
        self.base = 10

    @staticmethod
    def add(a, b):
        return a + b + MathUtil.base
    
obj = MathUtil()    
print(obj.add(2, 3))   