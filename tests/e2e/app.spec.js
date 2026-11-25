const { test, expect } = require("@playwright/test");

test.describe("Panel de Operaciones CI/CD - E2E", () => {
  test("muestra el estado saludable y permite crear, persistir y eliminar un elemento", async ({ page }) => {
    await page.goto("/");

    const healthBadge = page.getByTestId("health-badge");
    await expect(healthBadge).toContainText("Estado: OK");

    const uniqueTitle = `Despliegue-${Date.now()}`;
    await page.getByTestId("input-title").fill(uniqueTitle);
    await page.getByTestId("input-description").fill("Prueba E2E con Playwright");
    await page.getByTestId("select-status").selectOption("in_progress");
    await page.getByTestId("submit-btn").click();

    await expect(page.getByTestId("feedback")).toContainText("Elemento creado correctamente");
    const itemsList = page.getByTestId("items-list");
    await expect(itemsList).toContainText(uniqueTitle);

    await page.reload();
    await expect(page.getByTestId("items-list")).toContainText(uniqueTitle);

    const createdRow = page.locator(".item-row", { hasText: uniqueTitle });
    await createdRow.getByRole("button", { name: "Eliminar" }).click();
    await expect(page.getByTestId("feedback")).toContainText("Elemento eliminado");
    await expect(page.getByTestId("items-list")).not.toContainText(uniqueTitle);
  });

  test("el botón de simular error devuelve feedback de error HTTP 500", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("simulate-error-btn").click();
    await expect(page.getByTestId("feedback")).toContainText("Error simulado HTTP 500");
  });
});
