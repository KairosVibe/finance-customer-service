from pathlib import Path
from typing import Any

import yaml

from dialoguekit.task.flows.flows import FlowList, FlowSlot, Flow
from dialoguekit.task.flows.steps import FlowStep, CollectionFlowStep


class FlowLoader:

    def load_multi_yaml(self, paths: list[Path]) -> FlowList:
        final_flows: list[Flow] = []
        final_slots: dict[str, FlowSlot] = {}
        for path in paths:
            single_flow_list = self._load_single_yaml(path)
            final_flows.extend(single_flow_list.flows)
            final_slots.update(single_flow_list.slots)
        return FlowList(flows=final_flows, slots=final_slots)

    def _load_single_yaml(self, path: Path) -> FlowList:
        with  open(path, 'r', encoding='utf-8') as f:
            yaml_dict: dict[str, Any] = yaml.safe_load(f.read())
        loaded_slots = self._load_slots(yaml_dict.get('slots', {}))
        loaded_flows = self._load_flows(yaml_dict['flows'], loaded_slots)
        return FlowList(flows=loaded_flows, slots=loaded_slots)

    def _load_slots(self, slots_dict: dict[str, Any]) -> dict[str, FlowSlot]:
        loaded_slots: dict[str, FlowSlot] = {}
        for slot_name, slot_dict in slots_dict.items():
            loaded_slots[slot_name] = FlowSlot(
                slot_name=slot_name,
                type=slot_dict['type'],
                label=slot_dict['label'],
                description=slot_dict['description']
            )
        return loaded_slots

    def _load_flows(self,
                    flow_dict: dict[str, Any],
                    loaded_slots: dict[str, FlowSlot]) -> list[Flow]:
        loaded_flow: list[Flow] = []

        for flow_id, flow_dict in flow_dict.items():
            steps = [FlowStep.from_dict(step_data) for step_data in flow_dict['steps']]
            flow = Flow(
                id=flow_id,
                name=flow_dict['name'],
                description=flow_dict['description'],
                steps=steps,
                slots=self._build_flow_slot(steps, loaded_slots)
            )
            loaded_flow.append(flow)

        return loaded_flow

    def _build_flow_slot(self,
                         steps: list[FlowStep],
                         loaded_slots: dict[str, FlowSlot]) -> dict[str, FlowSlot]:
        final_flow_slots: dict[str, FlowSlot] = {}

        for step in steps:
            if not isinstance(step, CollectionFlowStep):
                continue

            slot_name = step.slot_name
            slot_definition = loaded_slots[slot_name]
            final_flow_slots[slot_name] = slot_definition

        return final_flow_slots


if __name__ == '__main__':
    flow_loader = FlowLoader()
    flow_list = flow_loader.load_multi_yaml([Path("system_flows.yml"), Path("user_flows.yml")])
    print(flow_list)