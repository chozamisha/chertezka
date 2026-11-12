# -*- coding: utf-8 -*-
"""Входные данные колеса КП-062215009-01 — из листа расчёта, не из приближений.

Числа совпадают с knowledge/calc/KP-062215009-01_calc.md и golden koleso_data.
"""
from __future__ import annotations

from .inputs import (
    AllowanceInputs,
    CastingInputs,
    CorePrintInputs,
    GatingInputs,
    MetaInputs,
    PartGeometryInputs,
    RiserInputs,
)
from ..spec.koleso_loader import KOLESO_PART_ID


def koleso_casting_inputs() -> CastingInputs:
    """Полный пакет исходных + принятых инженером параметров для рабочего колеса."""
    return CastingInputs(
        meta=MetaInputs(
            part_id=KOLESO_PART_ID,
            code="КП-062215009-01",
            name=("Колесо рабочее", "Отливка"),
            material=("Чугун ИЧХ28Н2", "ТУ 26-06-1484-87"),
            mass_stamp=420.0,
            scale_k=5.0,
            fmt="A2",
            dev="Шарабуров",
            chk="Степанова",
            rho=7.46e-6,
            rim_wall=25.0,
            bore_step_y=43.0,
        ),
        geometry=PartGeometryInputs(
            d_out=825.0,
            d_hub=240.0,
            d_bore=140.0,
            d_bore_lo=180.0,
            d_boss=340.0,
            h_hub=253.0,
            t_disk=40.0,
            h_ch=115.0,
            h_step=38.0,
            unit="mm",
        ),
        allowance=AllowanceInputs(
            # calc.md: ориентир 2,8 мм; ряд 11; чистовая → табл.6 = 5,2
            general_tolerance_mm=2.8,
            finish="Чистовая",
            allowance_row=11,
            # принятые инженером (верх формы / округление от 5,2)
            n_top=6.0,
            n_bot=5.0,
            n_face=5.0,
            n_hub_od=4.0,
            n_bore=4.0,
            n_boss=3.0,
            unit="mm",
        ),
        riser=RiserInputs(
            d_riser=300.0,
            d_neck=240.0,
            h_riser=300.0,
            core_scheme="A",
            unit="mm",
        ),
        gating=GatingInputs(
            f_pit_cm2=12.0,
            n_pit=2,
            ls_ratio_case="ICHX_academic_default",
            unit="cm2",
        ),
        cores=CorePrintInputs(
            # канал 115 → ряд 100-160; L=200 → столбец 160-250 → l_max=60
            section_mm=115.0,
            core_length_mm=200.0,
            l_print=60.0,
            h_print2=40.0,  # верт. знак Ст.2: engineer; gate табл.7 в P4.5.1
            unit="mm",
        ),
    )
