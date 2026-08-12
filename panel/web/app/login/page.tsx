export default function Login({ searchParams }: { searchParams: { e?: string } }) {
  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <form action="/api/login" method="POST" className="bg-panel border border-border rounded-2xl p-8 w-full max-w-sm flex flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold">Panel de Trading</h1>
          <p className="text-sm text-dim">Ingresa tu contraseña</p>
        </div>
        <input
          type="password"
          name="password"
          autoFocus
          placeholder="Contraseña"
          className="bg-panel2 border border-border rounded-lg px-3 py-2 outline-none focus:border-accent font-mono"
        />
        {searchParams?.e && <p className="text-loss text-xs">Contraseña incorrecta.</p>}
        <button className="bg-accent hover:opacity-90 text-white font-medium rounded-lg py-2 transition">Entrar</button>
      </form>
    </main>
  );
}
