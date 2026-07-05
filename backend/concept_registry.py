import json
from typing import Any

import httpx

from backend.data_provider.utils import normalize_code


class EastmoneyConceptRegistry:
    board_url = "https://push2.eastmoney.com/api/qt/clist/get"

    def __init__(self, fallback: "StaticConceptRegistry | None" = None) -> None:
        self.fallback = fallback or StaticConceptRegistry()

    def discover_concept_stocks(self) -> list[dict[str, str]]:
        params = {
            "pn": 1,
            "pz": 200,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "b:BK1188",
            "fields": "f12,f14",
        }
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(self.board_url, params=params)
                response.raise_for_status()
            rows = parse_eastmoney_board_payload(response.json())
        except Exception:
            rows = []
        return rows or self.fallback.discover_concept_stocks()


class StaticConceptRegistry:
    def discover_concept_stocks(self) -> list[dict[str, str]]:
        return [
            _stock("603728", "鸣志电器", "SH", "整机/系统集成", "空心杯电机、控制电机和运动控制系统", "控制电机、驱动系统、运动控制解决方案", ["人形机器人", "电机", "运动控制"]),
            _stock("002747", "埃斯顿", "SZ", "整机/系统集成", "工业机器人和自动化系统集成", "工业机器人、伺服系统、自动化产线", ["人形机器人", "机器人本体", "系统集成"]),
            _stock("300124", "汇川技术", "SZ", "减速器/伺服", "伺服驱动、控制器和工业自动化核心部件", "伺服系统、控制器、工业自动化产品", ["人形机器人", "伺服", "控制器"]),
            _stock("688017", "绿的谐波", "SH", "核心零部件", "谐波减速器", "谐波减速器、机电一体化执行器", ["人形机器人", "谐波减速器", "执行器"]),
            _stock("002050", "三花智控", "SZ", "核心零部件", "热管理和机器人执行器相关零部件", "热管理部件、机电执行器部件", ["人形机器人", "执行器", "热管理"]),
            _stock("002896", "中大力德", "SZ", "减速器/伺服", "减速器、电机和驱动器", "精密减速器、伺服电机、驱动器", ["人形机器人", "减速器", "电机"]),
            _stock("002472", "双环传动", "SZ", "减速器/伺服", "精密齿轮和传动系统", "精密齿轮、传动部件", ["人形机器人", "齿轮", "传动"]),
            _stock("688320", "禾川科技", "SH", "减速器/伺服", "伺服系统和工业控制", "伺服系统、PLC、工业控制产品", ["人形机器人", "伺服", "工业控制"]),
            _stock("688322", "奥比中光", "SH", "传感器", "3D视觉感知传感器", "3D视觉传感器、深度相机", ["人形机器人", "3D视觉", "传感器"]),
            _stock("002230", "科大讯飞", "SZ", "软件/算法", "语音识别、认知智能和AI算法", "语音识别、AI开放平台、大模型", ["人形机器人", "语音识别", "AI算法"]),
            _stock("002031", "巨轮智能", "SZ", "整机/系统集成", "工业机器人和智能装备", "工业机器人、智能装备、精密部件", ["人形机器人", "机器人本体", "智能装备"]),
            _stock("002527", "新时达", "SZ", "减速器/伺服", "机器人控制器和伺服系统", "机器人控制器、伺服驱动、工业机器人", ["人形机器人", "控制器", "伺服"]),
            _stock("002979", "雷赛智能", "SZ", "减速器/伺服", "运动控制和伺服系统", "步进系统、伺服系统、运动控制器", ["人形机器人", "运动控制", "伺服"]),
            _stock("300607", "拓斯达", "SZ", "整机/系统集成", "工业机器人和自动化应用", "工业机器人、注塑自动化、数控设备", ["人形机器人", "工业机器人", "系统集成"]),
            _stock("300024", "机器人", "SZ", "整机/系统集成", "机器人与智能制造装备", "工业机器人、移动机器人、智能装备", ["人形机器人", "机器人本体", "智能制造"]),
            _stock("300276", "三丰智能", "SZ", "整机/系统集成", "智能输送和工业机器人系统", "智能输送装备、工业机器人系统", ["人形机器人", "系统集成", "智能装备"]),
            _stock("300503", "昊志机电", "SZ", "核心零部件", "机器人执行器和精密传动相关部件", "主轴、转台、谐波减速器、执行器", ["人形机器人", "执行器", "精密传动"]),
            _stock("300580", "贝斯特", "SZ", "核心零部件", "精密零部件和机器人线性执行器相关业务", "精密零部件、滚珠丝杠、线性执行器", ["人形机器人", "丝杠", "执行器"]),
            _stock("301255", "通力科技", "SZ", "减速器/伺服", "减速机和传动设备", "减速机、传动设备", ["人形机器人", "减速器", "传动"]),
            _stock("688160", "步科股份", "SH", "减速器/伺服", "工业自动化控制和伺服驱动", "伺服系统、人机界面、低压变频器", ["人形机器人", "伺服", "控制"]),
            _stock("688698", "伟创电气", "SH", "减速器/伺服", "变频器和伺服系统", "变频器、伺服系统、控制系统", ["人形机器人", "伺服", "工控"]),
            _stock("688097", "博众精工", "SH", "整机/系统集成", "自动化设备和机器人应用", "自动化设备、机器人集成、智能制造产线", ["人形机器人", "自动化", "系统集成"]),
            _stock("688218", "江苏北人", "SH", "整机/系统集成", "工业机器人系统集成", "焊接机器人、自动化产线、系统集成", ["人形机器人", "工业机器人", "系统集成"]),
            _stock("688255", "凯尔达", "SH", "整机/系统集成", "焊接机器人和工业机器人应用", "焊接机器人、工业机器人系统", ["人形机器人", "工业机器人", "焊接机器人"]),
            _stock("688165", "埃夫特", "SH", "整机/系统集成", "工业机器人整机和系统集成", "工业机器人、喷涂机器人、系统集成", ["人形机器人", "机器人本体", "系统集成"]),
            _stock("688017", "绿的谐波", "SH", "核心零部件", "谐波减速器", "谐波减速器、机电一体化执行器", ["人形机器人", "谐波减速器", "执行器"]),
            _stock("688017", "绿的谐波", "SH", "核心零部件", "谐波减速器", "谐波减速器、机电一体化执行器", ["人形机器人", "谐波减速器", "执行器"]),
        ]


def parse_eastmoney_board_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = (payload.get("data") or {}).get("diff") or []
    return [
        _stock(
            str(item.get("f12") or ""),
            str(item.get("f14") or ""),
            _exchange_for(str(item.get("f12") or "")),
            "人形机器人概念",
            "东方财富人形机器人概念成分股",
            "外部概念源发现",
            ["人形机器人", "东方财富概念源"],
        )
        for item in rows
        if item.get("f12") and item.get("f14")
    ]


def _exchange_for(code: str) -> str:
    normalized = normalize_code(code)
    return "SH" if normalized.startswith(("6", "9")) else "SZ"


def _stock(
    code: str,
    name: str,
    exchange: str,
    industry_chain: str,
    industry_chain_detail: str,
    core_products: str,
    tags: list[str],
) -> dict[str, str]:
    return {
        "code": normalize_code(code),
        "name": name,
        "exchange": exchange,
        "industry_chain": industry_chain,
        "industry_chain_detail": industry_chain_detail,
        "core_products": core_products,
        "supply_chain_tags": json.dumps(tags, ensure_ascii=False),
    }


concept_registry = EastmoneyConceptRegistry()
