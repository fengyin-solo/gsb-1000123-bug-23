"""业务模块路由汇总。

这里统一按别名导入再暴露 ROUTERS：模块名有可能和内置名撞车（某个业务模块就叫 dict、list
这种名字时），按名字直接 import 会把内置类型覆盖掉，函数注解在运行时求值就会报
'module' object is not subscriptable。
"""
from __future__ import annotations

from app.routers import sample as router_sample
from app.routers import account as router_account
from app.routers import task as router_task
from app.routers import instrument as router_instrument
from app.routers import calibration as router_calibration
from app.routers import reagent as router_reagent
from app.routers import result as router_result
from app.routers import report as router_report
from app.routers import qc as router_qc
from app.routers import deviation as router_deviation
from app.routers import sample_storage as router_sample_storage
from app.routers import contract as router_contract
from app.routers import staff as router_staff
from app.routers import method as router_method
from app.routers import environment as router_environment
from app.routers import complain as router_complain
from app.routers import audit as router_audit
from app.routers import equipment_repair as router_equipment_repair
from app.routers import document as router_document

ROUTERS = [router_account, router_sample, router_task, router_instrument, router_calibration, router_reagent, router_result, router_report, router_qc, router_deviation, router_sample_storage, router_contract, router_staff, router_method, router_environment, router_complain, router_audit, router_equipment_repair, router_document]
