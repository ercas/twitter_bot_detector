#!/usr/bin/env python3

def unique_pairs(list_):
    """ Given a list, return every unique combination of two of its items

    Args:
        list_: A list to process

    Returns:
        A list of unique tuple pairs containing items from list_
    """

    pairs = []
    list_ = sorted(list_)
    len_ = len(list_)

    for i in range(len_ - 1):
        for seek in range(i + 1, len_):
            pairs.append((list_[i], list_[seek]))

    return pairs

class UniquePairsIterator(object):
    """ Iterable reimplementation of unique_pairs """

    def __init__(self, list_):
        """ Initializes UniquePairsIterator

        Args:
            list_: A list to process
        """

        self._list = list_
        self._len = len(list_)
        self._index = 0
        self._seek = 0

    def __iter__(self):
        return self

    def __next__(self):
        self._seek += 1

        if (self._seek == self._len):
            self._index += 1
            if (self._index == self._len - 1):
                raise StopIteration
            else:
                self._seek = self._index + 1

        return (self._list[self._index], self._list[self._seek])

def test():
    """ Run some checks to make sure the functions and classes are
    functioning properly """

    l = range(10)

    assert sorted(unique_pairs(l)) == sorted(UniquePairsIterator(l))
    assert sorted(unique_pairs(range(1, 5))) == [
        (1, 2), (1, 3), (1, 4),
                (2, 3), (2, 4),
                        (3, 4)
    ]

if (__name__ == "__main__"):
    test()
    print("All tests OK")
