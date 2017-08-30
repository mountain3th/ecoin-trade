import heapq

class HeapException(Exception):
    pass

class MinHeap(object):

    def __init__(self, heap):
        assert isinstance(heap, list)
        self.heap = heap
        heapq.heapify(self.heap)

    @property
    def heap_list(self):
        return self.heap

    def is_empty(self):
        return len(self.heap) == 0

    def peek(self):
        if len(self.heap) == 0:
            raise HeapException('Empty heap')
        return self.heap[0]

    def push(self, item):
        heapq.heappush(self.heap, item)

    def pop(self):
        return heapq.heappop(self.heap)

