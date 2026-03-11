/// <reference types="vite/client" />

interface Window {
  google?: {
    accounts: {
      id: {
        initialize: (config: {
          client_id: string;
          auto_select?: boolean;
          callback: (response: { credential: string }) => void;
        }) => void;
        renderButton: (
          element: HTMLElement,
          config: { theme: string; size: string; width: number; text: string },
        ) => void;
        disableAutoSelect: () => void;
      };
    };
  };
}
