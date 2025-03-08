import asyncio
import inspect
import logging
from datetime import datetime
from typing import Dict, Type, List, Callable, Tuple

# 配置日志记录器
logger = logging.getLogger(__name__)


class Event:
    """事件基类
    
    所有自定义事件都应该继承此类。
    每个事件对象都会自动记录创建时间。
    """
    def __init__(self):
        """初始化事件对象，记录创建时间"""
        self.create_time = datetime.now()

class EventManager:
    """事件管理器
    
    负责事件的注册、分发和处理。
    使用异步队列存储待处理的事件，并维护事件类型到处理器的映射。
    """
    def __init__(self):
        """初始化事件管理器
        
        创建事件队列和处理器映射字典，初始状态为未运行
        """
        # 事件队列，用于存储待处理的事件
        self.events = asyncio.Queue()
        # 事件类型到处理器列表的映射，每个处理器包含(handler, priority)
        self.handlers: Dict[Type[Event], List[Tuple[Callable[[Event], None], int]]] = {}
        # 事件循环运行状态标志
        self.running = False
        
        logger.debug("事件管理器初始化完成")

    async def add_event(self, event: Event):
        """添加事件到队列
        
        Args:
            event: 要添加的事件对象，必须是Event或其子类的实例
            
        Raises:
            TypeError: 当添加的对象不是Event或其子类的实例时
        """
        # 检查事件对象是否为Event或其子类的实例
        if not isinstance(event, Event):
            raise TypeError(f"事件对象必须是Event或其子类的实例，但收到了{type(event).__name__}类型")
            
        await self.events.put(event)

    def add_handler(self, event_type, handler, priority=0):
        """注册事件处理器
        
        Args:
            event_type: 事件类型，必须是Event的子类
            handler: 事件处理函数，必须是一个异步函数并且接受一个事件参数
            priority: 处理器优先级，数字越小优先级越高，默认为0
            
        Raises:
            TypeError: 当事件类型不是Event子类，或处理器不是异步函数，或处理器参数数量不正确时
        """
        # 检查event_type是否为Event的子类
        if not issubclass(event_type, Event):
            raise TypeError(f"事件类型必须是Event的子类，但收到了{event_type.__name__}")
        
        # 检查handler是否是异步函数
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError(f"事件处理器必须是异步函数，但收到了普通函数")
        
        # 检查handler是否只接受一个参数（事件对象）
        if len(inspect.signature(handler).parameters) != 1:
            raise TypeError(f"事件处理器必须只接受一个参数，但定义了{len(inspect.signature(handler).parameters)}个参数")
            
        logger.debug(f"注册处理器 {handler.__name__} 用于事件 {event_type.__name__}，优先级 {priority}")
        
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append((handler, priority))
        # 根据优先级排序处理器，优先级小的排在前面
        self.handlers[event_type].sort(key=lambda h: h[1])

    def remove_handler(self, event_type, handler):
        """移除事件处理器
        
        Args:
            event_type: 事件类型
            handler: 要移除的处理函数
        """
        if event_type in self.handlers:
            # 从处理器列表中查找并移除指定的处理器
            for i, (h, _) in enumerate(self.handlers[event_type]):
                if h == handler:
                    logger.debug(f"移除处理器 {handler.__name__} 用于事件 {event_type.__name__}")
                    self.handlers[event_type].pop(i)
                    break
                    
            # 如果该事件类型没有处理器了，则删除该事件类型
            if not self.handlers[event_type]:
                del self.handlers[event_type]
    
    async def handle_event(self, event):
        """处理单个事件
        
        Args:
            event: 要处理的事件对象
        """
        logger.debug(f"开始处理事件: {event.__class__.__name__}")
        
        # 查找该事件类型的所有处理器
        if event.__class__ in self.handlers:
            # 按优先级顺序依次调用每个处理器，并传入事件对象
            for handler, priority in self.handlers[event.__class__]:
                try:
                    logger.debug(f"调用处理器 {handler.__name__} (优先级: {priority})")
                    await handler(event)
                except Exception as e:
                    # 记录异常但不中断其他处理器的执行
                    logger.error(f"处理事件 {event.__class__.__name__} 时发生异常: {str(e)}", exc_info=True)

    async def run(self):
        """启动事件循环，开始处理事件队列中的事件"""
        logger.info("事件管理器开始运行")
        self.running = True
        while self.running:
            # 从队列中获取事件
            event = await self.events.get()
            # 创建任务处理事件，不阻塞事件循环
            await asyncio.create_task(self.handle_event(event))
    
    def stop(self):
        """停止事件循环"""
        logger.info("事件管理器停止运行")
        self.running = False

event_manager = EventManager()

# 注册事件处理器的装饰器
def register(event_type=None, priority=0):
    """注册事件处理器的装饰器
    
    可以通过以下方式使用:
    1. @register(EventType, priority=1) - 显式指定事件类型和优先级
    2. @register(EventType) - 显式指定事件类型，使用默认优先级
    3. @register(priority=1) - 从函数参数的类型注解自动推断事件类型，指定优先级
    4. @register - 从函数参数的类型注解自动推断事件类型，使用默认优先级
    
    Args:
        event_type: 可选，事件类型。如果不提供，将从处理函数的参数类型注解推断
        priority: 可选，处理器优先级，数字越小优先级越高，默认为0
        
    Returns:
        装饰器函数
        
    Raises:
        TypeError: 当无法从参数中推断事件类型时抛出
    """
    _func = None
    # 处理不带参数或只带priority参数的装饰器用法: @register
    if callable(event_type) and not isinstance(event_type, type):
        _func = event_type
        event_type = None
        
    def wrapper(func):
        # 如果没有指定event_type，那么默认使用func的第一个参数的类型
        nonlocal event_type
        if event_type is None:
            # 检查func的参数列表是否只有一个参数
            if len(inspect.signature(func).parameters) != 1:
                raise TypeError(f"事件处理器必须只接受一个参数，但定义了{len(inspect.signature(func).parameters)}个参数")
            
            # 检查参数是否有类型注解
            params = list(inspect.signature(func).parameters.items())
            if params[0][1].annotation is inspect.Parameter.empty:
                raise TypeError(f"无法自动推断事件类型，请为参数添加类型注解或显式指定事件类型")
            
            # 获取参数的类型注解作为事件类型
            event_type = params[0][1].annotation
            
        logger.debug(f"使用装饰器注册处理器 {func.__name__} 用于事件 {event_type.__name__}，优先级 {priority}")
        # 注册handler到事件管理器
        event_manager.add_handler(event_type, func, priority)
        return func
        
    # 处理装饰器调用方式
    if _func:
        return wrapper(_func)
    else:
        return wrapper
