from random import sample

_sample = sample
def sample(l, k):
    try:
        return _sample(l, k)
    except ValueError:
        return l


# inits :: [a] -> [[a]]
def inits(it):
    xs = []
    yield () #  For good measure
    for x in it:
        xs.append(x)
        yield tuple(xs)


def takeEvery(it, k, offset=0):
    for (i, x) in enumerate(it):
        if (i + offset) % k == 0:
            yield x
