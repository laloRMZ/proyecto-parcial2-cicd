const { test, expect } = require("@playwright/test");

test.describe("Login y CRUD Users - E2E", () => {
  test("rechaza credenciales inválidas y permite login + CRUD completo de usuarios", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("health-badge")).toContainText("Estado: OK");

    await page.getByTestId("login-username").fill("admin");
    await page.getByTestId("login-password").fill("incorrecta");
    await page.getByTestId("login-submit-btn").click();
    await expect(page.getByTestId("login-feedback")).toContainText("Credenciales inválidas");

    await page.getByTestId("login-username").fill("admin");
    await page.getByTestId("login-password").fill("admin123");
    await page.getByTestId("login-submit-btn").click();

    await expect(page.getByTestId("app-section")).toBeVisible();
    await expect(page.getByTestId("current-user-label")).toContainText("admin");

    const uname = `user_${Date.now()}`;
    await page.getByTestId("input-username").fill(uname);
    await page.getByTestId("input-email").fill(`${uname}@correo.com`);
    await page.getByTestId("input-fullname").fill("Usuario Prueba E2E");
    await page.getByTestId("select-role").selectOption("user");
    await page.getByTestId("input-password").fill("clave123");
    await page.getByTestId("submit-user-btn").click();

    await expect(page.getByTestId("feedback")).toContainText("Usuario creado correctamente");
    await expect(page.getByTestId("users-list")).toContainText(`@${uname}`);

    await page.reload();
    await expect(page.getByTestId("users-list")).toContainText(`@${uname}`);

    await page.getByTestId(`edit-btn-${uname}`).click();
    await page.getByTestId("input-fullname").fill("Usuario Editado E2E");
    await page.getByTestId("select-role").selectOption("viewer");
    await page.getByTestId("submit-user-btn").click();

    await expect(page.getByTestId("feedback")).toContainText("Usuario actualizado correctamente");
    await expect(page.getByTestId(`user-row-${uname}`)).toContainText("Usuario Editado E2E");
    await expect(page.getByTestId(`user-row-${uname}`)).toContainText("rol: viewer");

    await page.getByTestId(`delete-btn-${uname}`).click();
    await expect(page.getByTestId("feedback")).toContainText("Usuario eliminado");
    await expect(page.getByTestId("users-list")).not.toContainText(`@${uname}`);

    await page.getByTestId("logout-btn").click();
    await expect(page.getByTestId("login-section")).toBeVisible();
  });

  test("el botón de simular error devuelve feedback de error HTTP 500", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("login-username").fill("admin");
    await page.getByTestId("login-password").fill("admin123");
    await page.getByTestId("login-submit-btn").click();
    await expect(page.getByTestId("app-section")).toBeVisible();

    await page.getByTestId("simulate-error-btn").click();
    await expect(page.getByTestId("feedback")).toContainText("Error simulado HTTP 500");
  });
});
