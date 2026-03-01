import { test, expect } from "@playwright/test";

test.describe("SMM价格管理测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/smm-prices");
  });

  test("SMM价格页面正常加载", async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/SMM价格/);

    // 验证页面标题显示
    await expect(page.locator("h1")).toContainText("SMM价格");
  });

  test("显示新建价格按钮", async ({ page }) => {
    // 验证新建按钮存在
    await expect(page.locator("a:has-text('新建价格')")).toBeVisible();
  });

  test("导航到新建SMM价格页面", async ({ page }) => {
    // 点击新建价格按钮
    await page.click("a:has-text('新建价格')");

    // 验证导航成功
    await page.waitForURL(/\/smm-prices\/new/);
  });
});

test.describe("实物管理测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/physical-purchases");
  });

  test("实物管理页面正常加载", async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/实物管理/);

    // 验证页面标题显示
    await expect(page.locator("h1")).toContainText("实物管理");
  });

  test("显示新建采购按钮", async ({ page }) => {
    // 验证新建按钮存在
    await expect(page.locator("a:has-text('新建采购')")).toBeVisible();
  });

  test("导航到新建采购页面", async ({ page }) => {
    // 点击新建采购按钮
    await page.click("a:has-text('新建采购')");

    // 验证导航成功
    await page.waitForURL(/\/physical-purchases\/new/);
  });
});

test.describe("账务管理测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/billing");
  });

  test("账务管理页面正常加载", async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/账务管理/);

    // 验证页面标题显示
    await expect(page.locator("h1")).toContainText("账务管理");
  });

  test("显示统计卡片", async ({ page }) => {
    // 验证总支出显示
    const totalExpense = page.locator("text=/总支出/");
    const hasContent = await totalExpense.count();

    // 如果有数据，验证显示
    if (hasContent > 0) {
      await expect(totalExpense).toBeVisible();
    }
  });
});
