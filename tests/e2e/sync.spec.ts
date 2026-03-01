import { test, expect } from "@playwright/test";

test.describe("数据同步功能测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/import-sync");
  });

  test("数据同步页面正常加载", async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/数据同步/);

    // 验证页面标题显示
    await expect(page.locator("h1")).toContainText("数据同步");
  });

  test("显示导出数据区域", async ({ page }) => {
    // 验证导出数据标题
    await expect(page.locator("h2:has-text('导出数据')")).toBeVisible();

    // 验证导出为数据库文件按钮
    await expect(page.locator("a:has-text('导出为数据库文件')")).toBeVisible();

    // 验证导出为JSON文件按钮
    await expect(page.locator("a:has-text('导出为JSON文件')")).toBeVisible();

    // 验证推荐提示
    await expect(page.locator("text=/推荐使用数据库文件/")).toBeVisible();
  });

  test("显示导入数据区域", async ({ page }) => {
    // 验证导入数据标题
    await expect(page.locator("h2:has-text('导入数据')")).toBeVisible();

    // 验证文件上传区域
    await expect(page.locator("input[type='file']")).toBeVisible();

    // 验证上传提示文字
    await expect(page.locator("text=/点击上传/")).toBeVisible();
    await expect(page.locator("text=/支持 .db 或 .json 文件/")).toBeVisible();

    // 验证导入按钮
    await expect(page.locator("button:has-text('导入数据')")).toBeVisible();
  });

  test("显示使用说明", async ({ page }) => {
    // 验证使用说明标题
    await expect(page.locator("h3:has-text('使用说明')")).toBeVisible();

    // 验证说明步骤
    await expect(page.locator("text=/在设备A上点击/")).toBeVisible();
    await expect(page.locator("text=/将文件传输到设备B/")).toBeVisible();
    await expect(page.locator("text=/在设备B上点击/")).toBeVisible();
    await expect(page.locator("text=/系统会自动备份/")).toBeVisible();
  });

  test("显示注意事项", async ({ page }) => {
    // 验证注意警告框
    await expect(page.locator(".alert-warning")).toBeVisible();
    await expect(page.locator("text=/注意：导入数据会自动备份/")).toBeVisible();
  });

  test("文件上传区域交互", async ({ page }) => {
    // 获取文件上传区域
    const uploadArea = page.locator("label:has-text('点击上传')");

    // 验证鼠标悬停效果
    await uploadArea.hover();
    // 确保元素可见
    await expect(uploadArea).toBeVisible();
  });

  test("导出链接检查", async ({ page }) => {
    // 检查数据库导出链接
    const dbExportLink = page.locator("a[href*='/export-sync/format/db']");
    await expect(dbExportLink).toHaveAttribute("href", /\/export-sync\/format\/db/);

    // 检查JSON导出链接
    const jsonExportLink = page.locator("a[href*='/export-sync/format/json']");
    await expect(jsonExportLink).toHaveAttribute("href", /\/export-sync\/format\/json/);
  });

  test.describe("导入表单", () => {
    test("表单验证 - 无文件提交", async ({ page }) => {
      // 点击导入按钮而不选择文件
      await page.click("button[type='submit']");

      // 文件输入是required，表单应该不提交
      // 验证仍在同一页面
      expect(page.url()).toContain("/import-sync");
    });
  });
});
