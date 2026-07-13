export type WorkspaceSection =
  'dashboard' | 'groups' | 'documents' | 'search' | 'llm' | 'keys' | 'playground' | 'documentation';

export type GroupOption = {
  label: string;
  value: string;
};

export type StatTone = 'blue' | 'green' | 'amber' | 'red' | 'slate';
