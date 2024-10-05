from abc import ABC, abstractmethod


class Category(ABC):

    @abstractmethod
    def start_workflow(self):
        pass
