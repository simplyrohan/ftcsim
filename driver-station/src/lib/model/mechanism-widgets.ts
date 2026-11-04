import type { Component } from 'svelte';
import type { MechanismState } from './types';
import CustomMechanismView from '$lib/components/CustomMechanismView.svelte';
import DrivetrainView from '$lib/components/DrivetrainView.svelte';
export const mechanismWidgets = new Map<string,Component<{mechanism:MechanismState}>>([['mecanum',DrivetrainView],['tank',DrivetrainView],['custom',CustomMechanismView]]);
