import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App.jsx";

test("affiche le titre de l'application", () => {
  render(<App />);
  expect(screen.getByText("SenTransport")).toBeTruthy();
});
