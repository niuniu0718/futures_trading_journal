import { test, expect } from "@playwright/test";

test.describe("仪表盘功能测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("仪表盘页面正常加载", async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/期货交易记录系统/);

    // 验证导航栏存在
    const nav = page.locator("nav");
    await expect(nav).toBeVisible();

    // 验证关键导航链接
    await expect(page.locator("a[href='/']")).toContainText("仪表盘");
    await expect(page.locator("a[href='/trades']")).toContainText("交易记录");
    await expect(page.locator("a[href='/smm-prices']")).toContainText("SMM价格");
    await expect(page.locator("a[href='/billing']")).toContainText("账务管理");
    await expect(page.locator("a[href='/import-sync']")).toContainText("数据同步");
  });

  test("显示统计卡片", async ({ page }) => {
    // 验证平均开仓价卡片
    await expect(page.locator("text=/平均开仓价/")).toBeVisible();

    // 验证平均结算价卡片
    await expect(page.locator("text=/平均结算价/")).toBeVisible();

    // 验证SMM均价卡片
    await expect(page.locator("text=/SMM均价/")).toBeVisible();

    // 验证交易数卡片
    await expect(page.locator("text=/交易数/")).toBeVisible();
  });

  test("显示图表", async ({ page }) => {
    // 验证价格对比图表
    const priceChart = page.locator("#priceCompareChart");
    await expect(priceChart).toBeVisible();

    // 验证折扣对比图表
    const discountChart = page.locator("#discountCompareChart");
    await expect(discountChart).toBeVisible();
  });

  test("时间筛选功能", async ({ page }) => {
    // 输入开始日期
    await page.fill("#start_date", "2024-01-01");

    // 输入结束日期
    await page.fill("#end_date", "2024-12-31");

    // 点击筛选按钮
    await page.click("button:has-text('筛选')");

    // 等待页面重新加载
    await page.waitForLoadState("networkidle");

    // 验证URL包含筛选参数
    expect(page.url()).toContain("start_date=2024-01-01");
    expect(page.url()).toContain("end_date=2024-12-31");
  });

  test("清除筛选功能", async ({ page }) => {
    // 先设置筛选
    await page.fill("#start_date", "2024-01-01");
    await page.click("button:has-text('筛选')");
    await page.waitForLoadState("networkidle");

    // 点击清除按钮
    await page.click("a:has-text('清除')");

    // 验证返回首页且无筛选参数
    await page.waitForLoadState("networkidle");
    expect(page.url()).toBe("http://localhost:5001/");
  });

  test("SMM月份切换功能", async ({ page }) => {
    // 获取月份选择器
    const monthSelect = page.locator("#monthSelect");
    await expect(monthSelect).toBeVisible();

    // 选择不同的月份
    await monthSelect.selectOption({ index: 1 });

    // 等待页面更新
    await page.waitForLoadState("networkidle");

    // 验证URL包含月份参数
    expect(page.url()).toContain("month=");
  });

  test("导航到交易记录页面", async ({ page }) => {
    // 点击交易记录链接
    await page.click("a[href='/trades']");

    // 验证导航成功
    await page.waitForURL(/\/trades/);
    await expect(page.locator("h1")).toContainText("交易记录");
  });

  test("显示最近交易记录", async ({ page }) => {
    // 如果有交易记录，应该显示最近交易表格
    const recentTrades = page.locator("table.data-table");

    // 检查是否有交易记录或空状态提示
    const hasTable = await recentTrades.count();
    const hasEmptyState = await page.locator("text=/暂无交易记录/").count();

    expect(hasTable + hasEmptyState).toBeGreaterThan(0);
  });
});
