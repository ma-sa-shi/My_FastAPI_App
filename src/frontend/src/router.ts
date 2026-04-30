const routes: Record<string, () => Promise<void>> = {
  '/register': async () => {
    await import('./register');
    document.getElementById('app')!.innerHTML = '<register-view></register-view>';
  },
  '/login': async () => {
    await import('./login');
    document.getElementById('app')!.innerHTML = '<login-view></login-view>';
  },
  '/documents': async () => {
    await import('./manageDocs');
    document.getElementById('app')!.innerHTML = '<manage-docs-view></manage-docs-view>';
  },
  '/query': async () => {
    await import('./query');
    document.getElementById('app')!.innerHTML = '<query-view></query-view>';
  },
};

export const handleNavigation = async () => {
  //URLのドメインより後ろを取得
  const path = window.location.pathname;
  const routeAction = routes[path] || routes['/register'];
  if (routeAction) {
    await routeAction();
  }
};