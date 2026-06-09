import os
import re


def get_selected_username() -> str | None:
    """获取C盘用户文件夹下符合规则的用户名。

    规则：
    1. 单个英文字母开头 + 纯数字（数字个数不超过10个）
    2. 三个英文字母开头 + 纯数字（数字个数不超过10个）
    3. 多个匹配时，取纯数字部分最大的那个用户名

    Returns:
        匹配的用户名，若无匹配则返回 None
    """
    users_path = r"C:\Users"
    if not os.path.exists(users_path):
        return None

    # 获取所有子文件夹名称
    try:
        subfolders = [
            name for name in os.listdir(users_path)
            if os.path.isdir(os.path.join(users_path, name))
        ]
    except PermissionError:
        return None

    # 匹配规则：1个字母或3个字母 + 1~10个纯数字
    pattern = re.compile(r"^[a-zA-Z](?:[a-zA-Z]{2})?\d{1,10}$", re.ASCII)

    matched = [name for name in subfolders if pattern.fullmatch(name)]

    if not matched:
        return None

    if len(matched) == 1:
        return matched[0]

    # 多个匹配：去掉英文字母，比较纯数字部分，取最大的
    def extract_number(name: str) -> int:
        return int(re.sub(r"[a-zA-Z]", "", name))

    return max(matched, key=extract_number)


if __name__ == "__main__":
    result = get_selected_username()
    print(f"选中的用户名: {result}")