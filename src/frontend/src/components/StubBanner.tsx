export function StubBanner({ provider }: { provider: string }) {
  if (provider !== 'stub') return null;
  return (
    <div style={{
      background: '#f59e0b', color: '#000', padding: '6px 16px',
      fontSize: '13px', fontWeight: 600, textAlign: 'center', flexShrink: 0,
    }}>
      ⚠ Stub mode — set DATA_ANALYST_GEMINI_API_KEY in .env to enable live AI
    </div>
  );
}
