"""后台任务运行器 — QThread + 信号驱动的异步任务执行。

提供统一的异步任务接口，用于 PDF 批量处理、导入等长时间操作。
"""

from typing import Callable, Any, Optional
from PySide6.QtCore import QThread, Signal, QObject


class TaskSignals(QObject):
    """任务通信信号。"""
    started = Signal()
    progress = Signal(int, int, str)    # (current, total, message)
    finished = Signal(object)            # result
    error = Signal(str)                  # error_message
    cancelled = Signal()


class TaskRunner(QThread):
    """QThread 基类，封装后台任务的执行和信号通信。

    用法:
        runner = TaskRunner(task_func, arg1, arg2)
        runner.signals.progress.connect(my_handler)
        runner.signals.finished.connect(my_handler)
        runner.start()
    """

    def __init__(self, task_func: Callable, *args, **kwargs):
        """
        Args:
            task_func: 要在后台执行的可调用对象
            *args, **kwargs: 传递给 task_func 的参数
        """
        super().__init__()
        self._task_func = task_func
        self._args = args
        self._kwargs = kwargs
        self._cancelled = False
        self.signals = TaskSignals()

    def run(self):
        """在 QThread 中执行（由 start() 自动调用）。"""
        self.signals.started.emit()
        try:
            # 注入进度回调
            self._kwargs["progress_callback"] = self._on_progress
            self._kwargs["cancel_check"] = lambda: self._cancelled

            result = self._task_func(*self._args, **self._kwargs)

            if self._cancelled:
                self.signals.cancelled.emit()
            else:
                self.signals.finished.emit(result)

        except Exception as e:
            self.signals.error.emit(str(e))

    def cancel(self):
        """请求取消任务。"""
        self._cancelled = True

    def _on_progress(self, current: int, total: int, message: str = ""):
        """进度回调（由 task_func 内部调用）。"""
        self.signals.progress.emit(current, total, message)


class BatchTaskRunner(TaskRunner):
    """专门用于批量处理的 TaskRunner。

    输入列表，逐个处理，自动发送进度信号。
    """

    def __init__(self, items: list, item_func: Callable, **kwargs):
        """
        Args:
            items: 要处理的条目列表
            item_func: 对每个条目的处理函数，签名为 func(item, **kwargs) -> result
        """
        self._items = items
        self._item_func = item_func
        super().__init__(self._batch_run, **kwargs)

    def _batch_run(self, progress_callback=None, cancel_check=None, **kwargs):
        """批量执行。"""
        total = len(self._items)
        results = []
        errors = []

        for i, item in enumerate(self._items):
            if cancel_check and cancel_check():
                return {"results": results, "errors": errors, "cancelled": True}

            try:
                result = self._item_func(item, **kwargs)
                results.append(result)
            except Exception as e:
                errors.append({"item": str(item), "error": str(e)})

            if progress_callback:
                progress_callback(i + 1, total, f"处理中 ({i + 1}/{total})")

        return {"results": results, "errors": errors, "cancelled": False}
