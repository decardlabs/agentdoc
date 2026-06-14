"""
Obsidian 工具集
提供笔记读取、搜索、创建、更新等功能
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from datetime import datetime
import json

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class ObsidianTools:
    """Obsidian 工具集"""

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        if not os.path.exists(vault_path):
            logger.warning(f"Vault 路径不存在: {vault_path}")

    def list_notes(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出笔记

        Args:
            folder: 文件夹路径（相对于 vault）

        Returns:
            笔记列表
        """
        try:
            base_path = Path(self.vault_path)
            if folder:
                search_path = base_path / folder
            else:
                search_path = base_path

            if not search_path.exists():
                logger.warning(f"路径不存在: {search_path}")
                return []

            notes = []
            for md_file in search_path.rglob("*.md"):
                rel_path = md_file.relative_to(base_path)
                notes.append({
                    "file_path": str(rel_path),
                    "title": md_file.stem,
                    "size": md_file.stat().st_size,
                    "modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
                })

            return sorted(notes, key=lambda x: x["modified"], reverse=True)

        except Exception as e:
            logger.error(f"列出笔记失败: {str(e)}")
            return []

    def read_note(self, file_path: str) -> Optional[str]:
        """
        读取笔记内容

        Args:
            file_path: 文件路径（相对于 vault）

        Returns:
            笔记内容
        """
        try:
            full_path = Path(self.vault_path) / file_path

            if not full_path.exists():
                logger.warning(f"笔记不存在: {full_path}")
                return None

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return content

        except Exception as e:
            logger.error(f"读取笔记失败: {str(e)}")
            return None

    def create_note(
        self,
        title: str,
        content: str,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        创建笔记

        Args:
            title: 笔记标题
            content: 笔记内容
            folder: 文件夹（相对于 vault）
            tags: 标签列表

        Returns:
            创建的文件路径（相对于 vault）
        """
        try:
            base_path = Path(self.vault_path)

            if folder:
                target_dir = base_path / folder
            else:
                target_dir = base_path

            target_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}-{title}.md"
            file_path = target_dir / filename

            frontmatter = "---\n"
            frontmatter += f"title: {title}\n"
            frontmatter += f"created: {datetime.now().isoformat()}\n"
            if tags:
                frontmatter += f"tags: [{', '.join(tags)}]\n"
            frontmatter += "---\n\n"

            full_content = frontmatter + content

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            rel_path = file_path.relative_to(base_path)
            logger.info(f"笔记已创建: {rel_path}")

            return str(rel_path)

        except Exception as e:
            logger.error(f"创建笔记失败: {str(e)}")
            raise

    def update_note(self, file_path: str, content: str) -> bool:
        """
        更新笔记内容

        Args:
            file_path: 文件路径（相对于 vault）
            content: 新内容

        Returns:
            是否成功
        """
        try:
            full_path = Path(self.vault_path) / file_path

            if not full_path.exists():
                logger.warning(f"笔记不存在: {full_path}")
                return False

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"笔记已更新: {file_path}")
            return True

        except Exception as e:
            logger.error(f"更新笔记失败: {str(e)}")
            return False

    def get_note_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取笔记元数据

        Args:
            file_path: 文件路径（相对于 vault）

        Returns:
            元数据字典
        """
        try:
            full_path = Path(self.vault_path) / file_path

            if not full_path.exists():
                return {}

            content = self.read_note(file_path)
            if not content:
                return {}

            metadata = {
                "file_path": file_path,
                "title": full_path.stem,
                "size": full_path.stat().st_size,
                "modified": datetime.fromtimestamp(full_path.stat().st_mtime).isoformat(),
                "tags": [],
                "links": []
            }

            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if frontmatter_match:
                fm_text = frontmatter_match.group(1)
                for line in fm_text.split('\n'):
                    if line.startswith('tags:'):
                        tags_str = line[5:].strip()
                        if tags_str.startswith('[') and tags_str.endswith(']'):
                            metadata["tags"] = [t.strip() for t in tags_str[1:-1].split(',')]

            link_pattern = r'\[\[([^\]]+)\]\]'
            metadata["links"] = re.findall(link_pattern, content)

            return metadata

        except Exception as e:
            logger.error(f"获取元数据失败: {str(e)}")
            return {}

    def get_all_tags(self) -> List[str]:
        """
        获取所有标签

        Returns:
            标签列表
        """
        try:
            tags = set()

            for md_file in Path(self.vault_path).rglob("*.md"):
                content = self.read_note(str(md_file.relative_to(self.vault_path)))
                if not content:
                    continue

                frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if frontmatter_match:
                    fm_text = frontmatter_match.group(1)
                    for line in fm_text.split('\n'):
                        if line.startswith('tags:'):
                            tags_str = line[5:].strip()
                            if tags_str.startswith('[') and tags_str.endswith(']'):
                                file_tags = [t.strip() for t in tags_str[1:-1].split(',')]
                                tags.update(file_tags)

                tag_pattern = r'#(\w+)'
                content_tags = re.findall(tag_pattern, content)
                tags.update(content_tags)

            return sorted(list(tags))

        except Exception as e:
            logger.error(f"获取所有标签失败: {str(e)}")
            return []

    def search_in_file(self, query: str, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        在文件中搜索

        Args:
            query: 搜索关键词
            folder: 限制搜索文件夹

        Returns:
            搜索结果列表
        """
        try:
            results = []
            base_path = Path(self.vault_path)

            if folder:
                search_path = base_path / folder
            else:
                search_path = base_path

            for md_file in search_path.rglob("*.md"):
                content = self.read_note(str(md_file.relative_to(base_path)))
                if not content:
                    continue

                if query.lower() in content.lower():
                    rel_path = md_file.relative_to(base_path)

                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            results.append({
                                "file_path": str(rel_path),
                                "line_number": i + 1,
                                "line_content": line.strip(),
                                "title": md_file.stem
                            })

            return results

        except Exception as e:
            logger.error(f"在文件中搜索失败: {str(e)}")
            return []

    def get_backlinks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        获取反向链接

        Args:
            file_path: 文件路径（相对于 vault）

        Returns:
            反向链接列表
        """
        try:
            results = []
            base_path = Path(self.vault_path)
            target_name = Path(file_path).stem

            for md_file in base_path.rglob("*.md"):
                content = self.read_note(str(md_file.relative_to(base_path)))
                if not content:
                    continue

                if f"[[{target_name}]]" in content or f"[[{file_path}]]" in content:
                    rel_path = md_file.relative_to(base_path)
                    results.append({
                        "file_path": str(rel_path),
                        "title": md_file.stem
                    })

            return results

        except Exception as e:
            logger.error(f"获取反向链接失败: {str(e)}")
            return []
