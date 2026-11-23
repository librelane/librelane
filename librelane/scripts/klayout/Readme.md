## Reference
https://www.klayout.de/doc-qt5/code/index.html

## Notes

As of KLayout 0.30.13, using the built-in interpreter:

- The interpreter does not add the top-level directory to PYTHONPATH.
- A top-level exception results in a 0 exit. All exceptions must be caught.
- exit and sys.exit both do not propagate. Use this pattern:

```python3
try:
    import pya
    pya.Application.instance().exit(1)
except AttributeError:
    sys.exit(1)
```
