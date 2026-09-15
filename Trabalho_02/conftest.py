def pytest_itemcollected(item):
    doc = item.obj.__doc__
    item._nodeid = doc.strip().splitlines()[0] if doc else item.name[5:].replace("_", " ")
