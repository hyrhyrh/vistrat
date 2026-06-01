#!/usr/bin/env python3
"""
API性能测试脚本 v1.0
优化版本 - 包含认证、并发测试、详细统计
"""

import asyncio
import time
import statistics
import sys
from typing import List, Dict, Any, Optional
import json
import argparse

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

# 定义要测试的API端点
API_ENDPOINTS = {
    "认证相关": [
        {"method": "GET", "url": "/api/auth/verify", "name": "验证Token", "auth_required": True},
        {"method": "GET", "url": "/health", "name": "健康检查", "auth_required": False},
    ],
    "告警查询": [
        {"method": "GET", "url": "/api/alerts/search?size=15&page=1", "name": "搜索告警(15条)", "auth_required": False},
        {"method": "GET", "url": "/api/alerts/search?size=50&page=1", "name": "搜索告警(50条)", "auth_required": False},
        {"method": "GET", "url": "/api/alerts/stats", "name": "告警统计", "auth_required": False},
    ],
    "视频流管理": [
        {"method": "GET", "url": "/api/video-streams/", "name": "获取视频流列表", "auth_required": False},
        {"method": "GET", "url": "/api/video-streams/statistics/summary", "name": "视频流统计汇总", "auth_required": False},
        {"method": "GET", "url": "/api/video-streams/count/total", "name": "视频流总数", "auth_required": False},
    ],
    "视频文件管理": [
        {"method": "GET", "url": "/api/video-files/", "name": "搜索视频列表", "auth_required": False},
        {"method": "GET", "url": "/api/video-files/statistics/summary", "name": "视频统计信息", "auth_required": False},
    ],
    "分析结果": [
        {"method": "GET", "url": "/api/analysis-results/analysis-tasks?page=1&page_size=10", "name": "查询分析任务", "auth_required": False},
        {"method": "GET", "url": "/api/analysis-results/alerts?page=1&page_size=10", "name": "查询预警历史", "auth_required": False},
        {"method": "GET", "url": "/api/analysis-results/statistics", "name": "分析结果统计", "auth_required": False},
    ],
    "AI模型管理": [
        {"method": "GET", "url": "/api/ai-models/configs/", "name": "获取AI配置列表", "auth_required": False},
        {"method": "GET", "url": "/api/ai-models/providers", "name": "获取AI供应商", "auth_required": False},
        {"method": "GET", "url": "/api/ai-models/model-options", "name": "获取模型选项", "auth_required": False},
        {"method": "GET", "url": "/api/ai-models/statistics", "name": "AI统计信息", "auth_required": False},
    ],
    "性能监控": [
        {"method": "GET", "url": "/api/performance/system/overview", "name": "系统性能概览", "auth_required": False},
        {"method": "GET", "url": "/api/performance/health/comprehensive", "name": "系统健康检查", "auth_required": False},
        {"method": "GET", "url": "/api/performance/metrics/realtime", "name": "实时性能指标", "auth_required": False},
    ],
    "提示词模板": [
        {"method": "GET", "url": "/api/prompts/templates/list", "name": "模板列表", "auth_required": False},
        {"method": "GET", "url": "/api/prompts/templates/categories/list", "name": "分类列表", "auth_required": False},
    ],
    "AI供应商配置": [
        {"method": "GET", "url": "/api/ai-provider-configs/", "name": "获取供应商配置", "auth_required": False},
        {"method": "GET", "url": "/api/ai-provider-configs/simple", "name": "获取简单配置", "auth_required": False},
        {"method": "GET", "url": "/api/ai-provider-configs/statistics/summary", "name": "供应商统计", "auth_required": False},
    ],
    "安全监测大屏": [
        {"method": "GET", "url": "/api/api/safety/statistics", "name": "告警统计", "auth_required": False},
        {"method": "GET", "url": "/api/api/safety/recent-alerts", "name": "最近告警", "auth_required": False},
        {"method": "GET", "url": "/api/api/safety/algorithm-stats", "name": "算法统计", "auth_required": False},
    ],
    "MJPEG流媒体": [
        {"method": "GET", "url": "/api/mjpeg/health", "name": "MJPEG健康检查", "auth_required": False},
    ],
    "图片代理": [
        {"method": "GET", "url": "/api/image-proxy/test", "name": "测试图片代理", "auth_required": False},
    ],
}


class APIPerformanceTester:
    def __init__(self, base_url: str, auth_token: Optional[str] = None, repeat: int = 10):
        self.base_url = base_url
        self.auth_token = auth_token
        self.repeat = repeat
        self.results = []

    async def test_endpoint(self, session: aiohttp.ClientSession, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """测试单个API端点"""
        url = f"{self.base_url}{endpoint['url']}"
        method = endpoint['method']
        name = endpoint['name']
        auth_required = endpoint.get('auth_required', False)

        # 设置请求头
        headers = {}
        if auth_required and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        times = []
        errors = []
        status_codes = []

        for i in range(self.repeat):
            try:
                start = time.perf_counter()  # 使用更精确的计时器
                async with session.request(method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    await response.read()  # 确保完全读取响应
                    elapsed = (time.perf_counter() - start) * 1000  # 转换为毫秒
                    times.append(elapsed)
                    status_codes.append(response.status)
            except asyncio.TimeoutError:
                errors.append(f"请求{i+1}超时")
                times.append(10000)  # 超时记为10秒
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
            await asyncio.sleep(0.05)

        # 计算统计数据
        if times:
            # 过滤掉超时的数据计算真实性能
            valid_times = [t for t in times if t < 10000]

            if valid_times:
                avg_time = statistics.mean(valid_times)
                min_time = min(valid_times)
                max_time = max(valid_times)
                median_time = statistics.median(valid_times)

                # 计算标准差(稳定性指标)
                std_dev = statistics.stdev(valid_times) if len(valid_times) > 1 else 0

                # 计算P95和P99 (百分位数)
                sorted_times = sorted(valid_times)
                p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
                p99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
            else:
                avg_time = min_time = max_time = median_time = std_dev = p95 = p99 = 10000

            # 评级 - 基于P95而非平均值(更可靠)
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

    async def test_concurrent(self, session: aiohttp.ClientSession, endpoint: Dict[str, Any], concurrent: int = 10) -> Dict[str, Any]:
        """并发压力测试"""
        url = f"{self.base_url}{endpoint['url']}"

        async def single_request():
            start = time.perf_counter()
            try:
                async with session.request(endpoint['method'], url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    await response.read()
                    return (time.perf_counter() - start) * 1000, response.status
            except Exception:
                return 10000, 0

        # 并发执行
        start_time = time.perf_counter()
        results = await asyncio.gather(*[single_request() for _ in range(concurrent)])
        total_time = (time.perf_counter() - start_time) * 1000

        times = [r[0] for r in results]
        success = sum(1 for r in results if 200 <= r[1] < 300)

        return {
            "concurrent": concurrent,
            "total_time": round(total_time, 2),
            "avg_time": round(statistics.mean(times), 2),
            "success_rate": round(success / concurrent * 100, 2),
            "qps": round(concurrent / (total_time / 1000), 2) if total_time > 0 else 0
        }

    async def run_tests(self, test_concurrent: bool = False):
        """运行所有测试"""
        connector = aiohttp.TCPConnector(limit=100)  # 增加连接池大小
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
                    print(f"{status_icon} {result['name']:35s} | P95: {result['p95']:7.2f}ms | 成功率: {result['success_rate']:5.1f}% | 评级: {result['rating']}")

                    # 并发测试(仅对部分关键接口)
                    if test_concurrent and category in ["告警查询", "视频流管理", "分析结果"]:
                        concurrent_result = await self.test_concurrent(session, endpoint, concurrent=20)
                        result['concurrent_test'] = concurrent_result
                        print(f"   └─ 并发20: QPS={concurrent_result['qps']:.1f}, 平均耗时={concurrent_result['avg_time']:.2f}ms")

                self.results.append({
                    "category": category,
                    "endpoints": category_results
                })

    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("\n" + "="*120)
        report.append("API性能测试报告 v2.0")
        report.append("="*120)
        report.append(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
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

                # 收集性能差的API
                if endpoint['rating'] in ["差", "极差"] or endpoint['success_rate'] < 90:
                    all_poor_apis.append({
                        "category": category,
                        **endpoint
                    })

        # 性能不合格API汇总 + 优化建议
        if all_poor_apis:
            report.append("\n" + "="*120)
            report.append("⚠️  性能不合格API汇总与优化建议")
            report.append("="*120)

            for i, api in enumerate(all_poor_apis, 1):
                report.append(f"\n【问题 #{i}】")
                report.append(f"分类: {api['category']}")
                report.append(f"接口: {api['name']}")
                report.append(f"URL: {api['url']}")
                report.append(f"性能指标: 平均={api['avg_time']:.2f}ms, P95={api['p95']:.2f}ms, P99={api['p99']:.2f}ms")
                report.append(f"成功率: {api['success_rate']:.1f}%")
                report.append(f"稳定性: 标准差={api['std_dev']:.2f}ms")

                if api['errors']:
                    report.append(f"错误日志: {api['errors'][0]}")

                # 智能优化建议
                report.append("\n优化建议:")
                if "search" in api['url'] or "alerts" in api['url']:
                    report.append("  1. 添加Elasticsearch查询缓存 (10-60秒)")
                    report.append("  2. 优化ES查询DSL,减少聚合复杂度")
                    report.append("  3. 考虑使用游标(scroll)代替深分页")
                    report.append("  4. 添加Redis缓存热点查询")
                elif "statistics" in api['url'] or "summary" in api['url']:
                    report.append("  1. 使用Redis缓存统计结果 (5-30秒)")
                    report.append("  2. 考虑异步计算+定时刷新策略")
                    report.append("  3. 使用Elasticsearch聚合而非Python计算")
                elif "video-streams" in api['url']:
                    report.append("  1. 添加数据库查询索引")
                    report.append("  2. 使用连接池优化PostgreSQL查询")
                    report.append("  3. 减少JOIN操作,考虑冗余字段")
                elif api['p95'] > 2000:
                    report.append("  1. 检查数据库慢查询日志")
                    report.append("  2. 添加APM性能监控定位瓶颈")
                    report.append("  3. 考虑异步处理+轮询结果")

                if api['std_dev'] > 500:
                    report.append("  5. ⚠️ 标准差过大,响应时间不稳定,检查:")
                    report.append("     - 数据库连接池是否耗尽")
                    report.append("     - Elasticsearch是否有GC问题")
                    report.append("     - 网络抖动或资源竞争")

        # 统计摘要
        total_apis = sum(len(cat['endpoints']) for cat in self.results)
        excellent = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] == "优秀")
        good = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] == "良好")
        acceptable = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] == "可接受")
        poor = sum(1 for cat in self.results for e in cat['endpoints'] if e['rating'] in ["差", "极差"])

        report.append("\n" + "="*120)
        report.append("统计摘要")
        report.append("="*120)
        report.append(f"总测试接口数: {total_apis}")
        report.append(f"优秀 (P95<100ms): {excellent} ({excellent/total_apis*100:.1f}%)")
        report.append(f"良好 (P95<300ms): {good} ({good/total_apis*100:.1f}%)")
        report.append(f"可接受 (P95<1000ms): {acceptable} ({acceptable/total_apis*100:.1f}%)")
        report.append(f"性能差 (P95>1000ms): {poor} ({poor/total_apis*100:.1f}%)")

        if poor / total_apis > 0.2:
            report.append("\n⚠️  警告: 超过20%的API性能不达标,需要立即优化!")
        elif poor / total_apis > 0.1:
            report.append("\n⚠️  注意: 有超过10%的API性能较差,建议优化")
        else:
            report.append("\n✅ 总体性能良好")

        return "\n".join(report)

    def save_json_report(self, filename: str = "api_performance_report.json"):
        """保存JSON格式报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "base_url": self.base_url,
                "test_repeat": self.repeat,
                "standards": PERFORMANCE_STANDARDS,
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON报告已保存: {filename}")


async def main():
    parser = argparse.ArgumentParser(description='API性能测试工具')
    parser.add_argument('--url', default=BASE_URL, help='目标服务器URL')
    parser.add_argument('--token', help='认证Token (可选)')
    parser.add_argument('--repeat', type=int, default=10, help='每个接口测试次数 (默认10)')
    parser.add_argument('--concurrent', action='store_true', help='启用并发压力测试')
    args = parser.parse_args()

    print("="*80)
    print("API性能测试工具 v2.0")
    print("="*80)
    print(f"目标服务器: {args.url}")
    print(f"测试次数: {args.repeat}")
    print(f"并发测试: {'启用' if args.concurrent else '禁用'}")
    print(f"性能标准(基于P95): 优秀<100ms, 良好<300ms, 可接受<1000ms, 差<3000ms")

    tester = APIPerformanceTester(args.url, auth_token=args.token, repeat=args.repeat)
    await tester.run_tests(test_concurrent=args.concurrent)

    # 生成并显示报告
    report = tester.generate_report()
    print(report)

    # 保存报告
    tester.save_json_report("api_performance_report.json")

    # 保存文本报告
    with open("api_performance_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print("✅ 文本报告已保存: api_performance_report.txt")


if __name__ == "__main__":
    asyncio.run(main())
