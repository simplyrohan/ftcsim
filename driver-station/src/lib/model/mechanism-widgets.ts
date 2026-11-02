import type { Component } from 'svelte';
import type { MechanismState } from './types';
import CustomMechanismView from '$lib/components/CustomMechanismView.svelte';
import MecanumView from '$lib/components/MecanumView.svelte';
export const mechanismWidgets = new Map<string,Component<{mechanism:MechanismState}>>([['mecanum',MecanumView],['custom',CustomMechanismView]]);
