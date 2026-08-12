import { NextResponse } from "next/server";

export const runtime = "edge";
export async function POST(req: Request) {
  const form = await req.formData();
  const pw = String(form.get("password") ?? "");
  if (pw && pw === process.env.PANEL_PASSWORD) {
    const res = NextResponse.redirect(new URL("/", req.url), { status: 303 });
    res.cookies.set("panel_auth", pw, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
    return res;
  }
  return NextResponse.redirect(new URL("/login?e=1", req.url), { status: 303 });
}
