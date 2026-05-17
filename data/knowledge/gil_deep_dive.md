# Python GIL 深度解析

## 什么是 GIL？

**GIL**（Global Interpreter Lock，全局解释器锁）是 CPython（官方 Python 解释器）中的一个**互斥锁**。

它保证同一时刻**只有一个线程**可以执行 Python 字节码，从而避免了线程安全问题。

## 为什么需要 GIL？

- Python 的内存管理（引用计数）不是线程安全的
- 早期设计时为了简化 C 扩展的开发
- 避免复杂的线程同步问题

## GIL 的影响

### 1. 多线程在 CPU 密集型任务中几乎无加速
```python
# 多线程跑 CPU 密集任务，速度和单线程差不多