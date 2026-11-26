const { test, expect } = require("@playwright/test");

test.describe("Suite Parametrizada Frontend E2E - Login", () => {
  for (let i = 1; i <= 40; i++) {
    test(`Login inválido #${i} muestra mensaje de error`, async ({ page }) => {
      await page.goto("/");
      await page.getByTestId("login-username").fill(`invalido_${i}`);
      await page.getByTestId("login-password").fill(`clave_err_${i}`);
      await page.getByTestId("login-submit-btn").click();
      await expect(page.getByTestId("login-feedback")).toContainText("Credenciales inválidas");
    });
  }
});

test.describe("Suite Parametrizada Frontend E2E - CRUD Usuarios", () => {
  const roles = ["user", "admin", "viewer"];

  for (let i = 1; i <= 40; i++) {
    const role = roles[i % 3];
    test(`Crea usuario E2E #${i} con rol ${role} y lo muestra en lista`, async ({ page }) => {
      await page.goto("/");
      await page.getByTestId("login-username").fill("admin");
      await page.getByTestId("login-password").fill("admin123");
      await page.getByTestId("login-submit-btn").click();
      await expect(page.getByTestId("app-section")).toBeVisible();

      const uname = `pw_u_${i}_${Date.now()}`;
      await page.getByTestId("input-username").fill(uname);
      await page.getByTestId("input-email").fill(`${uname}@correo.com`);
      await page.getByTestId("input-fullname").fill(`Usuario E2E ${i}`);
      await page.getByTestId("select-role").selectOption(role);
      await page.getByTestId("input-password").fill("secret123");
      await page.getByTestId("submit-user-btn").click();

      await expect(page.getByTestId("feedback")).toContainText("Usuario creado correctamente");
      await expect(page.getByTestId(`user-row-${uname}`)).toContainText(`rol: ${role}`);
    });
  }
});

test.describe("Suite Parametrizada Frontend E2E - UI, Edición y Errores", () => {
  for (let i = 1; i <= 40; i++) {
    test(`Verificación de estado saludable, sesión y error simulado #${i}`, async ({ page }) => {
      await page.goto("/");
      await expect(page.getByTestId("health-badge")).toContainText("Estado: OK");

      await page.getByTestId("login-username").fill("admin");
      await page.getByTestId("login-password").fill("admin123");
      await page.getByTestId("login-submit-btn").click();
      await expect(page.getByTestId("current-user-label")).toContainText("admin");

      await page.getByTestId("simulate-error-btn").click();
      await expect(page.getByTestId("feedback")).toContainText("Error simulado HTTP 500");

      await page.getByTestId("logout-btn").click();
      await expect(page.getByTestId("login-section")).toBeVisible();
    });
  }
});
