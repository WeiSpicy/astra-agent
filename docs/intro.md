# FastAPI 简介
FastAPI 是一个现代、快速（高性能）的 Web 框架，用于构建 API。
它基于 Python 3.7+ 和标准类型提示。


# Python 高并发架构与 GIL 锁深度解析

## 1. 核心概念与现代并发模型
在 Python 软件工程实践中，并发（Concurrency）与并行（Parallelism）是优化系统吞吐量的两个核心维度。现代 Python 开发通常将并发任务分为两类：CPU 密集型（CPU-bound）任务，如大规模数据计算、图像处理或加密解密；以及 IO 密集型（IO-bound）任务，如网络请求、数据库查询及文件读写。
针对不同的任务属性，Python 提供了三种主流的解决方案：多线程（threading）、多进程（multiprocessing）以及基于标准库的异步编程（asyncio）。理解它们底层的底层差异与适用边界，是构建高性能 FastAPI 服务的基石。

## 2. 全局解释器锁（GIL）的底层阻碍
Python 官方的 CPython 解释器中，存在一个备受争议的底层机制——全局解释器锁（Global Interpreter Lock，简称 GIL）。GIL 是一个互斥锁，其核心作用是保护 Python 虚拟机内部的内存管理，防止多个线程同时执行 Python 字节码，从而避免引用计数（Reference Counting）在并发环境下发生竞态条件（Race Conditions）。
由于 GIL 的硬性限制，在任意给定时间片内，同一个 Python 进程中实际上有且仅有一个线程能够获得 CPU 的执行权。这就意味着，即便你在 8 核的 CPU 上开辟了 8 个线程跑纯计算任务，它们也只能在单核上轮流交替执行，多线程无法实现真正的多核并行计算。

## 3. 多线程与异步编程（asyncio）在 IO 密集型场景的应用
既然存在 GIL 锁，为什么多线程依然能在 IO 密集型场景下发挥作用？这是因为当某个线程执行到 IO 操作（例如等待网络数据返回）时，CPython 解释器会主动释放 GIL 锁，允许其他线程获取 CPU 执行权。因此，多线程在处理成百上千个网络请求时，能够通过线程切换掩盖 IO 等待时间。
而现代 Python 更推荐使用 asyncio 异步编程。asyncio 基于操作系统的事件循环（Event Loop）和非阻塞 IO 机制（如 Linux 的 epoll）。它采用单线程协作式调度，通过 `async` 和 `await` 关键字实现任务挂起。与多线程相比，异步编程几乎没有线程上下文切换的内核开销，内存占用极小，单单一个进程就能轻松应对数万个并发连接。

## 4. 多进程（Multiprocessing）破局 CPU 密集型任务
要真正榨干服务器的多核 CPU 算力，唯一的技术路径是采用多进程模型（Multiprocessing）。Python 的 `multiprocessing` 模块通过创建全新的子进程来绕过 GIL 锁。因为每个子进程都拥有自己独立的 CPython 解释器虚拟机、独立的内存空间以及独立的 GIL 锁，所以它们可以被操作系统真正调度到不同的 CPU 核心上，实现真正的物理并行。
但是，多进程是一把双刃剑。进程的创建和销毁伴随着巨大的内核开销，且由于进程间内存完全隔离，进行进程间通信（IPC，如使用 Pipe、Queue 或 Shared Memory）时，必须对数据进行序列化与反序列化（Pickle 过程），这会带来额外的 CPU 和性能损耗。