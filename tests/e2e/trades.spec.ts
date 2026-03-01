import { test, expect } from "@playwright/test";

test.describe("交易记录功能测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/trades");
  });

  test("交易记录页面正常加载", async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/交易记录/);

    // 验证页面标题显示
    await expect(page.locator("h1")).toContainText("交易记录");
  });

  test("显示筛选器", async ({ page }) => {
    // 验证状态筛选器
    await expect(page.locator("#status")).toBeVisible();

    // 验证品种筛选器
    await expect(page.locator("#product")).toBeVisible();

    // 验证日期筛选器
    await expect(page.locator("#start_date")).toBeVisible();
    await expect(page.locator("#end_date")).toBeVisible();

    // 验证筛选和清除按钮
    await expect(page.locator("button:has-text('筛选')")).toBeVisible();
    await expect(page.locator("a:has-text('清除')")).toBeVisible();
  });

  test("显示统计汇总", async ({ page }) => {
    // 验证总数量显示
    await expect(page.locator("text=/总数量/")).toBeVisible();

    // 验证总实物吨显示
    await expect(page.locator("text=/总实物吨/")).toBeVisible();

    // 验证平均开仓价显示
    await expect(page.locator("text=/平均开仓价/")).toBeVisible();

    // 验证SMM均价显示
    await expect(page.locator("text=/SMM均价/")).toBeVisible();
  });

  test("导航到新建交易页面", async ({ page }) => {
    // 点击新建交易按钮
    await page.click("a:has-text('新建交易')");

    // 验证导航成功
    await page.waitForURL(/\/trades\/new/);
    await expect(page.locator("h1")).toContainText("新建交易");
  });

  test("状态筛选功能", async ({ page }) => {
    // 选择"持仓中"状态
    await page.selectOption("#status", "open");

    // 点击筛选
    await page.click("button:has-text('筛选')");

    // 等待页面重新加载
    await page.waitForLoadState("networkidle");

    // 验证URL包含筛选参数
    expect(page.url()).toContain("status=open");
  });

  test("日期范围筛选功能", async ({ page }) => {
    // 输入日期范围
    await page.fill("#start_date", "2024-01-01");
    await page.fill("#end_date", "2024-12-31");

    // 点击筛选
    await page.click("button:has-text('筛选')");

    // 等待页面重新加载
    await page.waitForLoadState("networkidle");

    // 验证URL包含筛选参数
    expect(page.url()).toContain("start_date=2024-01-01");
    expect(page.url()).toContain("end_date=2024-12-31");
  });

  test("清除筛选功能", async ({ page }) => {
    // 先设置筛选条件
    await page.selectOption("#status", "open");
    await page.click("button:has-text('筛选')");
    await page.waitForLoadState("networkidle");

    // 点击清除按钮
    await page.click("a:has-text('清除')");

    // 验证返回交易记录页面且无筛选参数
    await page.waitForLoadState("networkidle");
    expect(page.url()).toBe("http://localhost:5001/trades");
  });

  test("显示批量操作按钮", async ({ page }) => {
    // 验证批量删除按钮存在
    await expect(page.locator("button:has-text('批量删除')")).toBeVisible();

    // 验证批量导出按钮存在
    await expect(page.locator("button:has-text('批量导出')")).toBeVisible();
  });

  test("表格排序功能", async ({ page }) => {
    // 点击日期列头进行排序
    const dateHeader = page.locator("th:has-text('日期')");
    await dateHeader.click();

    // 等待页面重新加载
    await page.waitForLoadState("networkidle");

    // 验证URL包含排序参数
    expect(page.url()).toContain("order_by=trade_date");
  });

  test.describe("新建交易表单", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/trades/new");
    });

    test("表单正常显示", async ({ page }) => {
      // 验证必填字段存在
      await expect(page.locator("#trade_date")).toBeVisible();
      await expect(page.locator("#product_id")).toBeVisible();
      await expect(page.locator("#direction")).toBeVisible();
      await expect(page.locator("#quantity")).toBeVisible();
      await expect(page.locator("#entry_price")).toBeVisible();

      // 验证提交按钮
      await expect(page.locator("button[type='submit']")).toBeVisible();
    });

    test("表单验证 - 提交空表单", async ({ page }) => {
      // 提交空表单
      await page.click("button[type='submit']");

      // 等待验证错误显示（表单应该仍在同一页面）
      await page.waitForLoadState("networkidle");

      // 验证URL没有跳转
      expect(page.url()).toContain("/trades/new");
    });

    test("填充表单字段", async ({ page }) => {
      // 填写交易日期
      await page.fill("#trade_date", "2024-03-01");

      // 填写数量
      await page.fill("#quantity", "100");

      // 填写开仓价
      await page.fill("#entry_price", "50000");

      // 验证字段已填充
      await expect(page.locator("#trade_date")).toHaveValue("2024-03-01");
      await expect(page.locator("#quantity")).toHaveValue("100");
      await expect(page.locator("#entry_price")).toHaveValue("50000");
    });
  });

  test.describe("数据导入导出", () => {
    test("显示导入导出按钮", async ({ page }) => {
      // 验证导入按钮
      await expect(page.locator("button:has-text('导入')")).toBeVisible();

      // 验证导出按钮
      await expect(page.locator("a:has-text('导出')")).toBeVisible();
    });
  });
});
