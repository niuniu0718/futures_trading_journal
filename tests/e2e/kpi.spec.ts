import { test, expect } from '@playwright/test';

test.describe('KPI追踪功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/kpi');
  });

  test('显示KPI页面标题', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('KPI追踪');
  });

  test('显示统计卡片', async ({ page }) => {
    await expect(page.locator('text=本月实际采购')).toBeVisible();
    await expect(page.locator('text=本月预测')).toBeVisible();
    await expect(page.locator('text=降本达成')).toBeVisible();
  });

  test('打开添加记录模态框', async ({ page }) => {
    await page.click('button:has-text("添加记录")');
    await expect(page.locator('#formModal')).toBeVisible();
    await expect(page.locator('#modalTitle')).toContainText('添加KPI记录');
  });

  test('品种筛选功能', async ({ page }) => {
    await page.selectOption('#product', '碳酸锂');
    await page.click('button:has-text("筛选")');
    // 验证URL包含筛选参数
    expect(page.url()).toContain('product=碳酸锂');
  });

  test('添加新KPI记录', async ({ page }) => {
    await page.click('button:has-text("添加记录")');

    // 填写表单
    await page.fill('#month', '2026-03');
    await page.selectOption('#product_name', '碳酸锂');
    await page.fill('#actual_quantity', '100');
    await page.fill('#actual_avg_price', '150000');
    await page.fill('#forecast_quantity', '120');
    await page.fill('#forecast_avg_price', '148000');

    // 提交表单
    await page.click('button:has-text("保存")');

    // 验证重定向回列表页
    await expect(page).toHaveURL('/kpi');
  });

  test('编辑KPI记录', async ({ page }) => {
    // 假设列表中至少有一条记录
    const editButton = page.locator('button:has-text("编辑")').first();
    if (await editButton.isVisible()) {
      await editButton.click();
      await expect(page.locator('#formModal')).toBeVisible();
      await expect(page.locator('#modalTitle')).toContainText('编辑KPI记录');
    }
  });

  test('删除KPI记录', async ({ page }) => {
    // 假设列表中至少有一条记录
    const deleteForm = page.locator('form.inline').first();
    if (await deleteForm.isVisible()) {
      // 监听对话框
      page.on('dialog', dialog => {
        expect(dialog.message()).toContain('确定要删除');
        dialog.accept();
      });

      await deleteForm.locator('button:has-text("删除")').click();
    }
  });
});
