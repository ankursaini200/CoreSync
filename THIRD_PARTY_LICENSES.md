# Third-Party Licenses & Attributions

CoreSync relies upon open-source software libraries. Gratitude is expressed to the maintainers and contributors of these projects.

---

## 1. PySide6 (Qt for Python)
- **License**: LGPLv3 / Commercial
- **Upstream Project**: [The Qt Company](https://www.qt.io/) / [Qt for Python](https://wiki.qt.io/Qt_for_Python)
- **Role in CoreSync**: Graphical user interface components, Qt event loop, native vector rendering via `QPainter`.
- **Usage Compliance**: Dynamically linked via standard Python package bindings; source modifications are not made to Qt binaries.

## 2. psutil
- **License**: BSD 3-Clause
- **Upstream Project**: [Giampaolo Rodola](https://github.com/giampaolo/psutil)
- **Role in CoreSync**: Cross-platform system and process telemetry (CPU utilization, core frequency, RAM usage, process RSS, CPU affinity masks).

## 3. NumPy
- **License**: BSD 3-Clause
- **Upstream Project**: [NumPy Developers](https://numpy.org/)
- **Role in CoreSync**: Contiguous numerical arrays, high-performance chunk slicing for Data Parallelism, and mathematical kernel functions.

## 4. Matplotlib
- **License**: PSF (Python Software Foundation) based Matplotlib License
- **Upstream Project**: [Matplotlib Development Team](https://matplotlib.org/)
- **Role in CoreSync**: Scalability benchmarking curves, Amdahl's Law theoretical asymptote plotting, and comparative Gantt visualizers.

## 5. pytest & pytest-qt
- **License**: MIT License
- **Upstream Project**: [pytest-dev](https://github.com/pytest-dev/pytest)
- **Role in CoreSync**: Automated regression test framework and headless Qt application integration testing.

