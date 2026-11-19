const { test, expect } = require('@playwright/test');

const ADMIN = {
  username: 'ci-e2e-admin',
  password: 'ci-e2e-admin-password',
};

async function login(page, credentials) {
  await page.goto('/login/');
  await page.getByLabel('Usuário').fill(credentials.username);
  await page.getByLabel('Senha').fill(credentials.password);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('button', { name: new RegExp(credentials.username) })).toBeVisible();
}

test('login rejeita credenciais invalidas e aceita o administrador E2E', async ({ page }) => {
  await page.goto('/login/');
  await page.getByLabel('Usuário').fill('ci-e2e-invalid');
  await page.getByLabel('Senha').fill('senha-incorreta');
  await page.getByRole('button', { name: 'Entrar' }).click();

  await expect(page).toHaveURL(/\/login\/$/);
  await expect(
    page.locator('#message-container').getByText('Usuario ou senha invalidos.', { exact: true })
  ).toBeVisible();

  await login(page, ADMIN);
  await expect(page.getByRole('link', { name: 'Auditoria', exact: true })).toBeVisible();
});
