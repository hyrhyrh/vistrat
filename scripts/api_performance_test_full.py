#!/usr/bin/env python3
"""
完整API性能测试脚本 v3.0
包含GET/POST/PUT/DELETE等所有HTTP方法的性能测试
"""

import asyncio
import time
import statistics
import sys
import uuid
from typing import List, Dict, Any, Optional
import json
import argparse
from datetime import datetime

# 检查依赖
try:
    import aiohttp
except ImportError:
    print("❌ 缺少依赖: pip install aiohttp")
    sys.exit(1)

BASE_URL = "http://localhost:16532"

# 定义性能标准（毫秒）
PERFORMANCE_STANDARDS = {
    "excellent": 100,    # <100ms 优秀
    "good": 300,         # <300ms 良好
    "acceptable": 1000,  # <1000ms 可接受
    "poor": 3000         # <3000ms 差
    # >3000ms 极差
}

# 定义要测试的API端点（包含所有HTTP方法）
API_ENDPOINTS = {
    "认证相关 (POST)": [
        {
            "method": "POST",
            "url": "/api/auth/login",
            "name": "用户登录",
            "auth_required": False,
            "body": {
                "username": "test_user",
                "password": "test_password"
            }
        },
    ],
    "视频流管理 (CRUD)": [
        {
            "method": "POST",
            "url": "/api/video-streams/",
            "name": "创建视频流",
            "auth_required": False,
            "body": {
                "name": f"测试流_{int(time.time())}",
                "stream_url": "rtsp://example.com/stream",
                "description": "性能测试创建的流",
                "status": "OFFLINE"
            }
        },
        {
            "method": "GET",
            "url": "/api/video-streams/",
            "name": "获取视频流列表",
            "auth_required": False
        },
    ],
    "提示词模板 (CRUD)": [
        {
            "method": "POST",
            "url": "/api/prompts/create",
            "name": "创建提示词模板",
            "auth_required": False,
            "body": {
                "name": f"测试模板_{int(time.time())}",
                "category": "测试分类",
                "content": "这是一个性能测试模板",
                "variables": []
            }
        },
        {
            "method": "GET",
            "url": "/api/prompts/templates/list",
            "name": "查询模板列表",
            "auth_required": False
        },
    ],
    "AI供应商配置 (CRUD)": [
        {
            "method": "POST",
            "url": "/api/ai-provider-configs/",
            "name": "创建AI供应商配置",
            "auth_required": False,
            "body": {
                "provider": "test_provider",
                "model_name": "test-model",
                "api_key": "test-key-123",
                "base_url": "https://api.example.com",
                "is_active": False,
                "priority": 1,
                "max_tokens": 1000,
                "temperature": 0.7
            }
        },
        {
            "method": "GET",
            "url": "/api/ai-provider-configs/",
            "name": "获取供应商配置列表",
            "auth_required": False
        },
    ],
    "流监控服务 (POST操作)": [
        {
            "method": "POST",
            "url": "/api/stream-monitor/streams/batch-health-check",
            "name": "批量健康检查",
            "auth_required": False,
            "body": {
                "stream_ids": []
            }
        },
    ],
    "AI模型管理 (POST)": [
        {
            "method": "POST",
            "url": "/api/ai-models/select-model",
            "name": "智能选择AI模型",
            "auth_required": False,
            "body": {
                "task_type": "image_analysis",
                "required_capabilities": ["object_detection"],
                "context": {
                    "image_count": 10,
                    "urgency": "normal"
                }
            }
        },
        {
            "method": "POST",
            "url": "/api/ai-models/test-config",
            "name": "测试AI配置",
            "auth_required": False,
            "body": {
                "provider": "moonshot",
                "model_name": "moonshot-v1-8k",
                "api_key": "test-key"
            }
        },
    ],
    "告警管理": [
        {
            "method": "GET",
            "url": "/api/alerts/search?size=15&page=1",
            "name": "搜索告警(15条)",
            "auth_required": False
        },
        {
            "method": "GET",
            "url": "/api/alerts/stats",
            "name": "告警统计",
            "auth_required": False
        },
        {
            "method": "DELETE",
            "url": "/api/alerts/history",
            "name": "清理告警历史",
            "auth_required": False,
            "params": {"days": 365}
        },
    ],
    "分析任务 (CRUD)": [
        {
            "method": "POST",
            "url": "/api/stream-tasks/",
            "name": "创建分析任务",
            "auth_required": False,
            "body": {
                "name": f"测试任务_{int(time.time())}",
                "stream_id": "test-stream-id",
                "algorithm": "object_detection",
                "config": {},
                "enabled": False
            }
        },
        {
            "method": "GET",
            "url": "/api/stream-tasks/",
            "name": "获取任务列表",
            "auth_required": False
        },
    ],
    "实时流管理 (CRUD)": [
        {
            "method": "POST",
            "url": "/api/streams/create",
            "name": "创建实时流",
            "auth_required": False,
            "body": {
                "name": f"实时流_{int(time.time())}",
                "url": "rtsp://test.example.com/stream",
                "type": "rtsp"
            }
        },
    ],
    "性能监控 (POST)": [
        {
            "method": "POST",
            "url": "/api/performance/circuit-breakers/reset",
            "name": "重置熔断器",
            "auth_required": False
        },
    ],
}


class APIPerformanceTester:
    def __init__(self, base_url: str, auth_token: Optional[str] = None, repeat: int = 5):
        self.base_url = base_url
        self.auth_token = auth_token
        self.repeat = repeat
        self.results = []
        self.created_resources = {
            "video_streams": [],
            "prompts": [],
            "ai_configs": [],
            "tasks": [],
            "streams": []
        }

    async def test_endpoint(self, session: aiohttp.ClientSession, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """测试单个API端点"""
        url = f"{self.base_url}{endpoint['url']}"
        method = endpoint['method']
        name = endpoint['name']
        auth_required = endpoint.get('auth_required', False)
        body = endpoint.get('body')
        params = endpoint.get('params')

        # 设置请求头
        headers = {"Content-Type": "application/json"}
        if auth_required and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        times = []
        errors = []
        status_codes = []
        responses = []

        for i in range(self.repeat):
            try:
                start = time.perf_counter()

                # 根据方法类型发送请求
                if method == "GET":
                    async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_data = await response.read()
                        elapsed = (time.perf_counter() - start) * 1000
                        times.append(elapsed)
                        status_codes.append(response.status)
                        if response.status == 200:
                            try:
                                responses.append(await response.json() if response_data else {})
                            except:
                                responses.append({})

                elif method == "POST":
                    async with session.post(url, headers=headers, json=body, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_data = await response.read()
                        elapsed = (time.perf_counter() - start) * 1000
                        times.append(elapsed)
                        status_codes.append(response.status)
                        if response.status in [200, 201]:
                            try:
                                resp_json = await response.json() if response_data else {}
                                responses.append(resp_json)
                                # 保存创建的资源ID用于后续清理
                                self._save_resource_id(endpoint, resp_json)
                            except:
                                responses.append({})

                elif method == "PUT":
                    async with session.put(url, headers=headers, json=body, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_data = await response.read()
                        elapsed = (time.perf_counter() - start) * 1000
                        times.append(elapsed)
                        status_codes.append(response.status)
                        if response.status == 200:
                            try:
                                responses.append(await response.json() if response_data else {})
                            except:
                                responses.append({})

                elif method == "DELETE":
                    async with session.delete(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_data = await response.read()
                        elapsed = (time.perf_counter() - start) * 1000
                        times.append(elapsed)
                        status_codes.append(response.status)

                elif method == "PATCH":
                    async with session.patch(url, headers=headers, json=body, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_data = await response.read()
                        elapsed = (time.perf_counter() - start) * 1000
                        times.append(elapsed)
                        status_codes.append(response.status)

            except asyncio.TimeoutError:
                errors.append(f"请求{i+1}超时")
                times.append(10000)
                status_codes.append(0)
            except aiohttp.ClientError as e:
                errors.append(f"请求{i+1}网络错误: {type(e).__name__}")
                times.append(10000)
                status_codes.append(0)
            except Exception as e:
                errors.append(f"请求{i+1}未知错误: {str(e)[:50]}")
                times.append(10000)
                status_codes.append(0)

            # 避免过快请求
            await asyncio.sleep(0.1)

        # 计算统计数据
        if times:
            valid_times = [t for t in times if t < 10000]

            if valid_times:
                avg_time = statistics.mean(valid_times)
                min_time = min(valid_times)
                max_time = max(valid_times)
                median_time = statistics.median(valid_times)
                std_dev = statistics.stdev(valid_times) if len(valid_times) > 1 else 0

                sorted_times = sorted(valid_times)
                p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
                p99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
            else:
                avg_time = min_time = max_time = median_time = std_dev = p95 = p99 = 10000

            # 评级
            if p95 < PERFORMANCE_STANDARDS["excellent"]:
                rating = "优秀"
                color = "green"
            elif p95 < PERFORMANCE_STANDARDS["good"]:
                rating = "良好"
                color = "green"
            elif p95 < PERFORMANCE_STANDARDS["acceptable"]:
                rating = "可接受"
                color = "yellow"
            elif p95 < PERFORMANCE_STANDARDS["poor"]:
                rating = "差"
                color = "orange"
            else:
                rating = "极差"
                color = "red"
        else:
            avg_time = min_time = max_time = median_time = std_dev = p95 = p99 = 0
            rating = "失败"
            color = "red"

        # 计算成功率
        success_count = sum(1 for code in status_codes if 200 <= code < 300)
        success_rate = (success_count / len(status_codes) * 100) if status_codes else 0

        return {
            "name": name,
            "url": endpoint['url'],
            "method": method,
            "avg_time": round(avg_time, 2),
            "min_time": round(min_time, 2),
            "max_time": round(max_time, 2),
            "median_time": round(median_time, 2),
            "std_dev": round(std_dev, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "success_rate": round(success_rate, 2),
            "rating": rating,
            "color": color,
            "errors": errors,
            "status_codes": status_codes,
            "test_count": self.repeat
        }

    def _save_resource_id(self, endpoint: Dict[str, Any], response: Dict[str, Any]):
        """保存创建的资源ID用于后续清理"""
        try:
            if "video-streams" in endpoint['url'] and endpoint['method'] == "POST":
                if 'id' in response:
                    self.created_resources['video_streams'].append(response['id'])
            elif "prompts" in endpoint['url'] and endpoint['method'] == "POST":
                if 'id' in response:
                    self.created_resources['prompts'].append(response['id'])
            elif "ai-provider-configs" in endpoint['url'] and endpoint['method'] == "POST":
                if 'id' in response:
                    self.created_resources['ai_configs'].append(response['id'])
            elif "stream-tasks" in endpoint['url'] and endpoint['method'] == "POST":
                if 'id' in response:
                    self.created_resources['tasks'].append(response['id'])
            elif "streams" in endpoint['url'] and endpoint['method'] == "POST":
                if 'id' in response:
                    self.created_resources['streams'].append(response['id'])
        except:
            pass

    async def cleanup_resources(self, session: aiohttp.ClientSession):
        """清理测试创建的资源"""
        print("\n" + "="*80)
        print("清理测试资源...")
        print("="*80)

        headers = {"Content-Type": "application/json"}
        cleanup_count = 0

        # 清理视频流
        for stream_id in self.created_resources['video_streams']:
            try:
                url = f"{self.base_url}/api/video-streams/{stream_id}"
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in [200, 204]:
                        cleanup_count += 1
                        print(f"✅ 已删除视频流: {stream_id}")
            except Exception as e:
                print(f"⚠️  删除视频流失败 {stream_id}: {str(e)[:50]}")

        # 清理提示词模板
        for prompt_id in self.created_resources['prompts']:
            try:
                url = f"{self.base_url}/api/prompts/{prompt_id}"
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in [200, 204]:
                        cleanup_count += 1
                        print(f"✅ 已删除提示词: {prompt_id}")
            except Exception as e:
                print(f"⚠️  删除提示词失败 {prompt_id}: {str(e)[:50]}")

        # 清理AI配置
        for config_id in self.created_resources['ai_configs']:
            try:
                url = f"{self.base_url}/api/ai-provider-configs/{config_id}"
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in [200, 204]:
                        cleanup_count += 1
                        print(f"✅ 已删除AI配置: {config_id}")
            except Exception as e:
                print(f"⚠️  删除AI配置失败 {config_id}: {str(e)[:50]}")

        # 清理任务
        for task_id in self.created_resources['tasks']:
            try:
                url = f"{self.base_url}/api/stream-tasks/{task_id}"
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in [200, 204]:
                        cleanup_count += 1
                        print(f"✅ 已删除任务: {task_id}")
            except Exception as e:
                print(f"⚠️  删除任务失败 {task_id}: {str(e)[:50]}")

        # 清理流
        for stream_id in self.created_resources['streams']:
            try:
                url = f"{self.base_url}/api/streams/{stream_id}"
                async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in [200, 204]:
                        cleanup_count += 1
                        print(f"✅ 已删除流: {stream_id}")
            except Exception as e:
                print(f"⚠️  删除流失败 {stream_id}: {str(e)[:50]}")

        print(f"\n✅ 清理完成，共删除 {cleanup_count} 个测试资源")

    async def run_tests(self):
        """运行所有测试"""
        connector = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            for category, endpoints in API_ENDPOINTS.items():
                print(f"\n{'='*80}")
                print(f"测试分类: {category}")
                print(f"{'='*80}")

                category_results = []
                for endpoint in endpoints:
                    result = await self.test_endpoint(session, endpoint)
                    category_results.append(result)

                    # 实时显示结果
                    status_icon = "✅" if result['rating'] in ["优秀", "良好"] else "⚠️" if result['rating'] == "可接受" else "❌"
                    print(f"{status_icon} {result['name']:35s} | {result['method']:6s} | P95: {result['p95']:7.2f}ms | 成功率: {result['success_rate']:5.1f}% | 评级: {result['rating']}")

                self.results.append({
                    "category": category,
                    "endpoints": category_results
                })

            # 清理测试资源
            await self.cleanup_resources(session)

    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("\n" + "="*120)
        report.append("完整API性能测试报告 v3.0 (包含POST/PUT/DELETE)")
        report.append("="*120)
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"目标服务器: {self.base_url}")
        report.append(f"每个接口测试次数: {self.repeat}")
        report.append(f"性能标准(基于P95): 优秀<100ms, 良好<300ms, 可接受<1000ms, 差<3000ms")

        all_poor_apis = []

        for category_result in self.results:
            category = category_result['category']
            endpoints = category_result['endpoints']

            report.append(f"\n## {category}")
            report.append("-" * 120)
            report.append(f"{'接口名称':<35} {'方法':<8} {'平均':<10} {'P95':<10} {'P99':<10} {'标准差':<10} {'成功率':<10} {'评级':<10}")
            report.append("-" * 120)

            for endpoint in endpoints:
                report.append(
                    f"{endpoint['name']:<35} "
                    f"{endpoint['method']:<8} "
                    f"{endpoint['avg_time']:<10.2f} "
                    f"{endpoint['p95']:<10.2f} "
                    f"{endpoint['p99']:<10.2f} "
                    f"{endpoint['std_dev']:<10.2f} "
                    f"{endpoint['success_rate']:<10.1f}% "
                    f"{endpoint['rating']:<10}"
                )

                if endpoint['rating'] in ["差", "极差"] or endpoint['success_rate'] < 90:
                    all_poor_apis.append({
                        "category": category,
                        **endpoint
                    })

        # 性能不合格API汇总
        if all_poor_apis:
            report.append("\n" + "="*120)
            report.append("⚠️  性能不合格API汇总与优化建议")
            report.append("="*120)

            for i, api in enumerate(all_poor_apis, 1):
                report.append(f"\n【问题 #{i}】")
                report.append(f"分类: {api['category']}")
                report.append(f"接口: {api['name']}")
                report.append(f"方法: {api['method']}")
                report.append(f"URL: {api['url']}")
                report.append(f"性能指标: 平均={api['avg_time']:.2f}ms, P95={api['p95']:.2f}ms, P99={api['p99']:.2f}ms")
                report.append(f"成功率: {api['success_rate']:.1f}%")
                report.append(f"稳定性: 标准差={api['std_dev']:.2f}ms")

                if api['errors']:
                    report.append(f"错误日志: {api['errors'][0]}")

                # 针对不同HTTP方法的优化建议
                report.append("\n优化建议:")
                if api['method'] == "POST":
                    report.append("  1. 检查数据验证逻辑是否过于复杂")
                    report.append("  2. 优化数据库写入操作，考虑批量插入")
                    report.append("  3. 使用异步任务处理耗时操作")
                    report.append("  4. 添加请求幂等性校验缓存")
                elif api['method'] == "PUT":
                    report.append("  1. 优化数据库更新查询，添加索引")
                    report.append("  2. 减少不必要的数据验证")
                    report.append("  3. 使用乐观锁而非悲观锁")
                elif api['method'] == "DELETE":
                    report.append("  1. 使用软删除代替物理删除")
                    report.append("  2. 异步清理关联数据")
                    report.append("  3. 添加删除操作缓存")
                elif api['method'] == "GET":
                    report.append("  1. 添加Redis缓存")
                    report.append("  2. 优化数据库查询，添加索引")
                    report.append("  3. 使用分页和游标优化大数据查询")

        # 统计摘要
        total_apis = sum(len(cat['endpoints']) for cat in self.results)
        excellent = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] == "优秀")
        good = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] == "良好")
        acceptable = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] == "可接受")
        poor = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] in ["差", "极差"])

        # 按HTTP方法统计
        method_stats = {}
        for cat in self.results:
            for e in cat['endpoints']:
                method = e['method']
                if method not in method_stats:
                    method_stats[method] = {"total": 0, "excellent": 0}
                method_stats[method]["total"] += 1
                if e['rating'] == "优秀":
                    method_stats[method]["excellent"] += 1

        report.append("\n" + "="*120)
        report.append("统计摘要")
        report.append("="*120)
        report.append(f"总测试接口数: {total_apis}")
        report.append(f"优秀 (P95<100ms): {excellent} ({excellent/total_apis*100:.1f}%)")
        report.append(f"良好 (P95<300ms): {good} ({good/total_apis*100:.1f}%)")
        report.append(f"可接受 (P95<1000ms): {acceptable} ({acceptable/total_apis*100:.1f}%)")
        report.append(f"性能差 (P95>1000ms): {poor} ({poor/total_apis*100:.1f}%)")

        report.append("\n按HTTP方法统计:")
        for method, stats in sorted(method_stats.items()):
            report.append(f"  {method}: {stats['total']}个接口, {stats['excellent']}个优秀 ({stats['excellent']/stats['total']*100:.1f}%)")

        if poor / total_apis > 0.2:
            report.append("\n⚠️  警告: 超过20%的API性能不达标,需要立即优化!")
        elif poor / total_apis > 0.1:
            report.append("\n⚠️  注意: 有超过10%的API性能较差,建议优化")
        else:
            report.append("\n✅ 总体性能良好")

        return "\n".join(report)

    def save_json_report(self, filename: str = "api_performance_report_full.json"):
        """保存JSON格式报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "base_url": self.base_url,
                "test_repeat": self.repeat,
                "standards": PERFORMANCE_STANDARDS,
                "results": self.results,
                "created_resources": self.created_resources
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON报告已保存: {filename}")


async def main():
    parser = argparse.ArgumentParser(description='完整API性能测试工具 (包含POST/PUT/DELETE)')
    parser.add_argument('--url', default=BASE_URL, help='目标服务器URL')
    parser.add_argument('--token', help='认证Token (可选)')
    parser.add_argument('--repeat', type=int, default=5, help='每个接口测试次数 (默认5)')
    args = parser.parse_args()

    print("="*80)
    print("完整API性能测试工具 v3.0 (POST/PUT/DELETE)")
    print("="*80)
    print(f"目标服务器: {args.url}")
    print(f"测试次数: {args.repeat}")
    print(f"性能标准(基于P95): 优秀<100ms, 良好<300ms, 可接受<1000ms, 差<3000ms")
    print("⚠️  注意: 本测试会创建测试数据，测试结束后会自动清理")

    tester = APIPerformanceTester(args.url, auth_token=args.token, repeat=args.repeat)
    await tester.run_tests()

    # 生成并显示报告
    report = tester.generate_report()
    print(report)

    # 保存报告
    tester.save_json_report("api_performance_report_full.json")

    # 保存文本报告
    with open("api_performance_report_full.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print("✅ 文本报告已保存: api_performance_report_full.txt")


if __name__ == "__main__":
    asyncio.run(main())
