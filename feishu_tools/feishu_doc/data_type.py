BLOCK_NAME_MAP: dict[str, int] = {
    'page': 1,
    'text': 2,
    'heading1': 3,
    'heading2': 4,
    'heading3': 5,
    'heading4': 6,
    'heading5': 7,
    'heading6': 8,
    'heading7': 9,
    'heading8': 10,
    'heading9': 11,
    'bullet': 12,
    'ordered': 13,
    'code': 14,
    'quote': 15,
    'todo': 17,
    'bitable': 18,
    'callout': 19,
    'chat_card': 20,
    'diagram': 21,
    'divider': 22,
    'file': 23,
    'grid': 24,
    'grid_column': 25,
    'iframe': 26,
    'image': 27,
    'isv': 28,
    'mindnote': 29,
    'sheet': 30,
    'table': 31,
    'table_cell': 32,
    'view': 33,
    'quote_container': 34,
    'task': 35,
    'okr': 36,
    'okr_objective': 37,
    'okr_key_result': 38,
    'okr_progress': 39,
    'add_ons': 40,
    'jira_issue': 41,
    'wiki_catalog': 42,
    'board': 43,
    'agenda': 44,
    'agenda_item': 45,
    'agenda_item_title': 46,
    'agenda_item_content': 47,
    'link_preview': 48,
    'source_synced': 49,
    'reference_synced': 50,
    'sub_page_list': 51,
    'ai_template': 52
}

BLOCK_DESC_MAP: dict[str, int] = {
    '页面': 1,
    '文本': 2,
    '标题 1': 3,
    '标题 2': 4,
    '标题 3': 5,
    '标题 4': 6,
    '标题 5': 7,
    '标题 6': 8,
    '标题 7': 9,
    '标题 8': 10,
    '标题 9': 11,
    '无序列表': 12,
    '有序列表': 13,
    '代码块': 14,
    '引用': 15,
    '待办事项': 17,
    '多维表格': 18,
    '高亮块': 19,
    '会话卡片': 20,
    '流程图 & UML': 21,
    '流程图': 21,
    'UML': 21,
    '分割线': 22,
    '文件': 23,
    '分栏': 24,
    '分栏列': 25,
    '内嵌': 26,
    '图片': 27,
    '开放平台小组件': 28,
    '思维笔记': 29,
    '电子表格': 30,
    '表格': 31,
    '表格单元格': 32,
    '视图': 33,
    '引用容器': 34,
    '任务': 35,
    'OKR': 36,
    'OKR Objective': 37,
    'OKR Key Result': 38,
    'OKR Progress': 39,
    '新版文档小组件': 40,
    'Jira 问题': 41,
    'Wiki 子页面列表(旧版)': 42,
    '画板': 43,
    '议程': 44,
    '议程项': 45,
    '议程项标题': 46,
    '议程项内容': 47,
    '链接预览': 48,
    '源同步块': 49,
    '引用同步块': 50,
    'Wiki 子页面列表(新版)': 51,
    'AI 模板': 52
}

# 小写化，去除空格，合并
BLOCK_TYPE_MAP = {
    k.lower().replace(' ', ''): v 
    for d in (BLOCK_NAME_MAP, BLOCK_DESC_MAP) 
    for k, v in d.items()
}

def get_block_type(block_type_name: str | int) -> int:
    if isinstance(block_type_name, int):
        return block_type_name
    block_type = BLOCK_TYPE_MAP.get(block_type_name.lower().replace(' ', ''))
    if block_type is None:
        raise ValueError(
            f"不支持的块类型: {block_type_name}, "
            f"支持的块类型: {list(BLOCK_NAME_MAP.keys())} 或 {list(BLOCK_DESC_MAP.keys())}"
        )
    return block_type